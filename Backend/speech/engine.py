"""
Master Speech Recognition Engine Orchestrator for J.A.R.V.I.S. Phase V1.2.
Coordinates IAudioSource, IVADEngine, IStreamingSTTProvider, TranscriptBuffer,
LanguageDetector, EndpointDetector, TranscriptCleaner, and EventBus dispatches.
"""
import uuid
import time
import asyncio
import logging
from typing import Optional, Callable, Dict, Any, List

from .config import SpeechConfig, speech_config
from .models import (
    AudioFrame,
    VADResult,
    STTResult,
    LanguageResult,
    EndpointResult,
    SpeechSession,
    SpeechState,
)
from .interfaces import (
    IAudioSource,
    IVADEngine,
    IStreamingSTTProvider,
    IEndpointDetector,
    ITranscriptBuffer,
    ILanguageDetector,
    ITranscriptCleaner,
    ISpeechRecoveryManager,
)
from .audio_sources import MicrophoneSource
from .vad import VADEngineFactory
from .streaming_stt import STTProviderFactory
from .transcript_buffer import TranscriptBuffer
from .language_detector import LanguageDetector
from .endpoint_detector import EndpointDetector
from .punctuation import TranscriptCleaner
from .recovery import SpeechRecoveryManager
from .metrics import speech_metrics, SpeechMetrics
from .events import (
    SpeechStartedEvent,
    SpeechPartialEvent,
    SpeechFinalEvent,
    SpeechEndedEvent,
    SpeechCancelledEvent,
    SpeechErrorEvent,
    LanguageDetectedEvent,
)
from brain.event_bus import event_bus, EventBus

logger = logging.getLogger("JARVIS_SpeechRecognitionEngine")


class SpeechRecognitionEngine:
    """
    Production-grade Speech Recognition Engine orchestrating real-time audio ingestion,
    VAD, streaming STT transcription, partial transcript buffering, language detection,
    intelligent endpointing, transcript cleanup, session state management, and cancellation.
    """

    def __init__(
        self,
        config: Optional[SpeechConfig] = None,
        audio_source: Optional[IAudioSource] = None,
        vad_engine: Optional[IVADEngine] = None,
        stt_provider: Optional[IStreamingSTTProvider] = None,
        endpoint_detector: Optional[IEndpointDetector] = None,
        transcript_buffer: Optional[ITranscriptBuffer] = None,
        language_detector: Optional[ILanguageDetector] = None,
        cleaner: Optional[ITranscriptCleaner] = None,
        recovery_manager: Optional[ISpeechRecoveryManager] = None,
        bus: Optional[EventBus] = None,
        conversation_engine: Optional[Any] = None,
    ):
        self.config = config or speech_config
        self.event_bus = bus or event_bus
        self.conversation_engine = conversation_engine

        self.audio_source = audio_source or MicrophoneSource(
            sample_rate=self.config.sample_rate,
            channels=self.config.channels,
            chunk_size=self.config.chunk_size_bytes,
        )
        self.vad_engine = vad_engine or VADEngineFactory.create_vad_engine(self.config.vad_provider)
        self.stt_provider = stt_provider or STTProviderFactory.create_provider(self.config.stt_provider)
        self.endpoint_detector = endpoint_detector or EndpointDetector(
            sensitivity=self.config.endpoint_sensitivity,
            max_pause_duration_ms=self.config.max_pause_duration_ms,
        )
        self.transcript_buffer = transcript_buffer or TranscriptBuffer()
        self.language_detector = language_detector or LanguageDetector()
        self.cleaner = cleaner or TranscriptCleaner()
        self.recovery_manager = recovery_manager or SpeechRecoveryManager(
            max_retries=self.config.max_retries,
            retry_delay_sec=self.config.retry_delay_sec,
        )
        self.metrics = speech_metrics

        self._active_session: Optional[SpeechSession] = None
        self._loop_task: Optional[asyncio.Task] = None
        self._callbacks: List[Callable[[SpeechFinalEvent], None]] = []
        self._paused: bool = False

    def register_final_transcript_callback(self, callback: Callable[[SpeechFinalEvent], None]) -> None:
        """Registers a callback for final clean transcript delivery."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def set_audio_source(self, source: IAudioSource) -> None:
        """Updates the active audio ingestion source dynamically."""
        self.audio_source = source

    def set_stt_provider(self, provider: IStreamingSTTProvider) -> None:
        """Updates the active STT provider dynamically."""
        self.stt_provider = provider

    def set_vad_engine(self, vad_engine: IVADEngine) -> None:
        """Updates the active VAD engine dynamically."""
        self.vad_engine = vad_engine

    def get_session(self) -> Optional[SpeechSession]:
        """Returns active speech session details."""
        return self._active_session

    async def start(self) -> SpeechSession:
        """Starts a new speech recognition session and launches non-blocking processing loop."""
        if self._active_session and self._active_session.state == SpeechState.LISTENING:
            return self._active_session

        session_id = f"spc_{uuid.uuid4().hex[:12]}"
        self._active_session = SpeechSession(
            session_id=session_id,
            started_at=time.time(),
            language=self.config.default_language,
            state=SpeechState.LISTENING,
        )
        self.metrics.total_sessions += 1
        self._paused = False

        # Reset pipeline component states
        self.vad_engine.reset()
        self.transcript_buffer.reset()
        self.endpoint_detector.reset()
        self.language_detector.reset()
        await self.stt_provider.connect()
        await self.audio_source.start()

        # Launch processing task
        self._loop_task = asyncio.create_task(self._process_pipeline_loop(self._active_session))
        logger.info(f"[SpeechEngine] Started speech recognition session '{session_id}'. Provider: '{self.stt_provider.name}'")
        return self._active_session

    async def pause(self) -> None:
        """Pauses audio processing without destroying the current session."""
        if self._active_session:
            self._paused = True
            self._active_session.state = SpeechState.PAUSED
            logger.info(f"[SpeechEngine] Paused speech recognition session '{self._active_session.session_id}'.")

    async def resume(self) -> None:
        """Resumes paused speech processing."""
        if self._active_session and self._paused:
            self._paused = False
            self._active_session.state = SpeechState.LISTENING
            logger.info(f"[SpeechEngine] Resumed speech recognition session '{self._active_session.session_id}'.")

    async def stop(self) -> Optional[SpeechFinalEvent]:
        """Gracefully stops speech recognition session and finalizes current transcript."""
        if not self._active_session:
            return None

        self._active_session.state = SpeechState.PROCESSING
        await self.audio_source.stop()

        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass

        final_event = await self._finalize_session(self._active_session, reason="user_stop")
        self._active_session.state = SpeechState.IDLE
        return final_event

    async def cancel(self) -> None:
        """Immediately interrupts speech processing, clears working state, and emits SpeechCancelledEvent."""
        if not self._active_session:
            return

        session_id = self._active_session.session_id
        self._active_session.state = SpeechState.CANCELLED
        self.metrics.total_cancellations += 1

        await self.audio_source.stop()
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass

        self.transcript_buffer.reset()

        # Emit SpeechCancelledEvent
        cancel_event = SpeechCancelledEvent(session_id=session_id, reason="immediate_cancellation")
        self.event_bus.emit("speech_cancelled", **cancel_event.__dict__)

        logger.info(f"[SpeechEngine] Cancelled speech recognition session '{session_id}'.")
        self._active_session = None

    async def _process_pipeline_loop(self, session: SpeechSession) -> None:
        """Core non-blocking processing loop consuming frames from IAudioSource."""
        speech_started_emitted = False
        language_resolved = False

        try:
            while session.state in (SpeechState.LISTENING, SpeechState.PAUSED):
                if self._paused:
                    await asyncio.sleep(0.05)
                    continue

                frame = await self.audio_source.read_frame()
                if not frame:
                    await asyncio.sleep(0.01)
                    continue

                session.audio_frames_processed += 1

                # 1. Process VAD
                vad_result = self.vad_engine.process_frame(frame)

                # Emit speech_started event when VAD signals speech start
                if vad_result.speech_started and not speech_started_emitted:
                    speech_started_emitted = True
                    start_event = SpeechStartedEvent(
                        session_id=session.session_id,
                        confidence=vad_result.confidence,
                    )
                    self.event_bus.emit("speech_started", **start_event.__dict__)

                # Skip streaming STT if no speech detected
                if not vad_result.is_speech and not speech_started_emitted:
                    continue

                # 2. Process Streaming STT
                stt_result = await self.stt_provider.process_audio_chunk(frame.data)
                self.metrics.record_stt_latency(stt_result.latency_ms)

                if stt_result.transcript:
                    # 3. Deduplicate via TranscriptBuffer
                    stable_text = self.transcript_buffer.add_partial(stt_result.transcript, stt_result.confidence)

                    # 4. Cascaded Language Resolution
                    if not language_resolved:
                        resolved_lang = stt_result.language
                        confidence_lang = stt_result.confidence
                        is_fallback = False

                        # If provider language missing, use LanguageDetector fallback
                        if not resolved_lang or self.config.language_detection_mode == "fallback_only":
                            lang_res = self.language_detector.detect_language(frame.data, stable_text)
                            resolved_lang = lang_res.language
                            confidence_lang = lang_res.confidence
                            is_fallback = lang_res.is_fallback

                        session.language = resolved_lang
                        language_resolved = True
                        self.metrics.record_language_confidence(confidence_lang)

                        lang_event = LanguageDetectedEvent(
                            session_id=session.session_id,
                            language=resolved_lang,
                            confidence=confidence_lang,
                            is_fallback=is_fallback,
                        )
                        self.event_bus.emit("language_detected", **lang_event.__dict__)

                    # Emit SpeechPartialEvent
                    self.metrics.total_partials += 1
                    self.metrics.record_confidence(stt_result.confidence)

                    partial_event = SpeechPartialEvent(
                        session_id=session.session_id,
                        transcript=stable_text,
                        confidence=stt_result.confidence,
                        language=session.language,
                        latency_ms=stt_result.latency_ms,
                    )
                    self.event_bus.emit("speech_partial", **partial_event.__dict__)

                    # 5. Evaluate Endpoint Detector
                    endpoint_res = self.endpoint_detector.evaluate(vad_result, stable_text)
                    if endpoint_res.is_endpoint:
                        logger.info(
                            f"[SpeechEngine] Endpoint confirmed for session '{session.session_id}' (Reason: {endpoint_res.reason})."
                        )
                        await self._finalize_session(session, reason=endpoint_res.reason)
                        break

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[SpeechEngine] Unexpected error in session '{session.session_id}': {e}")
            err_event = SpeechErrorEvent(
                session_id=session.session_id,
                error_type=type(e).__name__,
                message=str(e),
            )
            self.event_bus.emit("speech_error", **err_event.__dict__)
            recovered = await self.recovery_manager.handle_error(e, session.session_id)
            if not recovered:
                session.state = SpeechState.ERROR

    async def _finalize_session(self, session: SpeechSession, reason: str = "endpoint_reached") -> SpeechFinalEvent:
        """Finalizes session, cleans transcript, emits events, and hands off to Conversation Engine."""
        start_finalize = time.perf_counter()

        # Complete STT stream
        stt_final = await self.stt_provider.finish_stream()
        raw_transcript = self.transcript_buffer.finalize() or stt_final.transcript

        # Clean and punctuate final transcript
        clean_transcript = self.cleaner.clean(raw_transcript)
        session.duration_sec = time.time() - session.started_at
        confidence = stt_final.confidence if clean_transcript else 0.0

        final_delay_ms = (time.perf_counter() - start_finalize) * 1000.0
        self.metrics.total_finals += 1
        self.metrics.record_speech_duration(session.duration_sec)
        self.metrics.record_final_delay(final_delay_ms)

        # 1. Emit SpeechEndedEvent
        ended_event = SpeechEndedEvent(
            session_id=session.session_id,
            duration_sec=session.duration_sec,
            endpoint_reason=reason,
            confidence=confidence,
        )
        self.event_bus.emit("speech_ended", **ended_event.__dict__)

        # 2. Emit SpeechFinalEvent
        final_event = SpeechFinalEvent(
            session_id=session.session_id,
            transcript=clean_transcript,
            confidence=confidence,
            language=session.language,
            duration_sec=session.duration_sec,
        )
        self.event_bus.emit("speech_final", **final_event.__dict__)

        # 3. Notify registered callbacks
        for cb in self._callbacks:
            try:
                cb(final_event)
            except Exception as e:
                logger.error(f"[SpeechEngine] Callback error: {e}")

        # 4. Handoff single final transcript to Conversation Engine if available
        if self.conversation_engine and clean_transcript:
            try:
                import inspect

                if inspect.iscoroutinefunction(getattr(self.conversation_engine, "process_turn", None)):
                    asyncio.create_task(
                        self.conversation_engine.process_turn(
                            session_id=session.session_id,
                            turn_text=clean_transcript,
                        )
                    )
            except Exception as e:
                logger.error(f"[SpeechEngine] Handoff to Conversation Engine failed: {e}")

        logger.info(
            f"[SpeechEngine] Finalized session '{session.session_id}'. Duration: {session.duration_sec:.2f}s, Transcript: '{clean_transcript}'"
        )
        return final_event


# Global singleton speech recognition engine instance
speech_engine = SpeechRecognitionEngine()
