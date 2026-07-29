"""
Master Voice Output Engine Orchestrator for J.A.R.V.I.S. Phase V1.4.
Coordinates VoiceConfig, TextPreprocessor, SentenceSegmenter, ITTSProvider,
AudioCache, PlaybackEngine, IAudioOutput, and EventBus dispatches.
"""
import uuid
import time
import inspect
import asyncio
import logging
from typing import Optional, Dict, Any, List, Union, Callable

from .config import VoiceConfig, voice_config
from .models import (
    VoiceProfile,
    AudioChunk,
    TTSResult,
    PlaybackState,
    PlaybackSession,
)
from .interfaces import (
    ITextPreprocessor,
    ISentenceSegmenter,
    ITTSProvider,
    IAudioOutput,
    IAudioCache,
    IPlaybackEngine,
)
from .text_preprocessor import TextPreprocessor
from .sentence_segmenter import SentenceSegmenter
from .audio_cache import AudioCache
from .audio_outputs import MockAudioOutput, DesktopSpeakerOutput, FileOutput, WebSocketOutput, MobileAudioOutput
from .providers import TTSProviderFactory, MockTTSProvider
from .playback_engine import PlaybackEngine
from .metrics import voice_metrics, VoiceMetrics
from .events import (
    SpeechSynthesisStarted,
    SpeechChunkGenerated,
    SpeechPlaybackStarted,
    SpeechPlaybackPaused,
    SpeechPlaybackResumed,
    SpeechPlaybackCompleted,
    SpeechPlaybackCancelled,
    SpeechPlaybackError,
)
from brain.event_bus import event_bus, EventBus

logger = logging.getLogger("JARVIS_VoiceEngine")


class VoiceEngine:
    """
    Production-grade Voice Output Engine orchestrating text preprocessing, sentence segmentation,
    streaming TTS synthesis, audio LRU caching, queue playback, and event lifecycle dispatches.
    """

    def __init__(
        self,
        config: Optional[VoiceConfig] = None,
        preprocessor: Optional[ITextPreprocessor] = None,
        segmenter: Optional[ISentenceSegmenter] = None,
        provider: Optional[ITTSProvider] = None,
        cache: Optional[IAudioCache] = None,
        playback_engine: Optional[IPlaybackEngine] = None,
        output_driver: Optional[IAudioOutput] = None,
        bus: Optional[EventBus] = None,
    ):
        self.config = config or voice_config
        self.event_bus = bus or event_bus

        self.preprocessor = preprocessor or TextPreprocessor()
        self.segmenter = segmenter or SentenceSegmenter()
        self.provider = provider or TTSProviderFactory.create_provider(self.config.tts_provider)
        self.cache = cache or (AudioCache(max_size=self.config.cache_size) if self.config.cache_enabled else None)
        self.output_driver = output_driver or MockAudioOutput()
        self.playback_engine = playback_engine or PlaybackEngine(output_driver=self.output_driver)
        self.metrics = voice_metrics

        self.current_voice_profile = VoiceProfile(
            id=self.config.default_voice_id,
            provider=self.provider.name,
            language=self.config.default_language,
            gender=self.config.default_gender,
            name="Default Voice Profile",
            sample_rate=self.config.sample_rate,
        )

        self._active_session: Optional[PlaybackSession] = None
        self._subscribe_conversation_events()

    def _subscribe_conversation_events(self) -> None:
        """Subscribes to V1.3 Conversation Engine response ready events."""
        try:
            self.event_bus.subscribe("ConversationResponseReady", self._handle_conversation_response_event)
        except Exception as e:
            logger.warning(f"[VoiceEngine] Could not subscribe to ConversationResponseReady event: {e}")

    def _handle_conversation_response_event(self, event: Any = None, **kwargs) -> None:
        """Handles incoming ConversationResponseReady event over EventBus."""
        data = event.data if hasattr(event, "data") else (event if isinstance(event, dict) else kwargs)
        assistant_response = (data.get("assistant_response") if isinstance(data, dict) else "").strip()
        turn_id = data.get("turn_id") if isinstance(data, dict) else None

        if not assistant_response:
            return

        if inspect.iscoroutinefunction(self.speak):
            asyncio.create_task(self.speak(assistant_response, turn_id=turn_id))
        else:
            asyncio.run(self.speak(assistant_response, turn_id=turn_id))

    def set_voice(self, voice: Union[VoiceProfile, str]) -> None:
        """Updates active voice profile dynamically."""
        if isinstance(voice, VoiceProfile):
            self.current_voice_profile = voice
        else:
            self.current_voice_profile.id = voice

    def set_provider(self, provider: ITTSProvider) -> None:
        """Updates active TTS provider dynamically."""
        self.provider = provider
        self.current_voice_profile.provider = provider.name

    def set_output(self, driver: IAudioOutput) -> None:
        """Updates active audio output driver dynamically."""
        self.output_driver = driver
        if hasattr(self.playback_engine, "set_output_driver"):
            self.playback_engine.set_output_driver(driver)

    def get_metrics(self) -> Dict[str, Any]:
        """Returns snapshot summary of voice metrics telemetry."""
        return self.metrics.get_summary()

    def get_session(self) -> Optional[PlaybackSession]:
        """Returns active playback session."""
        return self._active_session

    async def speak(
        self,
        text_or_ssml: str,
        is_ssml: bool = False,
        turn_id: Optional[str] = None,
    ) -> TTSResult:
        """Full non-streaming synthesis pipeline returning TTSResult."""
        session = await self.stream(text_or_ssml, is_ssml=is_ssml, turn_id=turn_id)
        # Wait for playback loop completion
        while session.state in (PlaybackState.SYNTHESIZING, PlaybackState.PLAYING, PlaybackState.PAUSED):
            await asyncio.sleep(0.01)

        return TTSResult(
            session_id=session.playback_id,
            provider=self.provider.name,
            voice_profile=self.current_voice_profile,
            latency_ms=0.5,
            audio_duration_ms=session.duration_sec * 1000.0,
            cache_hit=False,
            chunk_count=session.audio_chunks_count,
            success=session.state == PlaybackState.COMPLETED,
        )

    async def stream(
        self,
        text_or_ssml: str,
        is_ssml: bool = False,
        turn_id: Optional[str] = None,
    ) -> PlaybackSession:
        """Streaming synthesis pipeline splitting text into sentences and streaming audio chunks."""
        playback_id = f"pbk_{uuid.uuid4().hex[:12]}"
        session = PlaybackSession(
            playback_id=playback_id,
            conversation_turn_id=turn_id,
            started_at=time.time(),
            state=PlaybackState.SYNTHESIZING,
            voice=self.current_voice_profile,
            provider=self.provider.name,
        )
        self._active_session = session
        self.metrics.total_sessions += 1

        # 1. Emit SpeechSynthesisStarted
        start_event = SpeechSynthesisStarted(
            playback_id=playback_id,
            turn_id=turn_id,
            text=text_or_ssml,
            voice_id=self.current_voice_profile.id,
            provider=self.provider.name,
        )
        self.event_bus.emit("SpeechSynthesisStarted", **start_event.__dict__)

        # 2. Text Preprocessing
        raw_text = text_or_ssml
        if self.config.preprocess_text and not is_ssml:
            raw_text = self.preprocessor.preprocess(text_or_ssml)

        # 3. Audio LRU Cache Check
        if self.cache:
            cache_key = AudioCache.generate_cache_key(raw_text, self.current_voice_profile.id, self.provider.name)
            cached_res = self.cache.get(cache_key)
            if cached_res:
                logger.info(f"[VoiceEngine] Cache HIT for playback '{playback_id}'.")
                # Fast playback of cached audio
                chunk = AudioChunk(
                    data=cached_res.audio_data,
                    index=1,
                    is_final=True,
                    duration_ms=cached_res.audio_duration_ms,
                )
                await self.playback_engine.start_playback(session)
                await self.playback_engine.enqueue_chunk(chunk)
                return session

        # 4. Launch Playback Engine
        await self.playback_engine.start_playback(session)

        # 5. Sentence Segmentation & Provider Streaming Loop
        asyncio.create_task(self._synthesize_and_stream_loop(session, raw_text, is_ssml))
        return session

    async def _synthesize_and_stream_loop(
        self,
        session: PlaybackSession,
        text_or_ssml: str,
        is_ssml: bool,
    ) -> None:
        """Asynchronously synthesizes sentence segments and enqueues audio chunks."""
        start_time = time.perf_counter()
        first_chunk = True

        try:
            sentences = self.segmenter.segment(text_or_ssml) if not is_ssml else [text_or_ssml]
            all_chunks: List[bytes] = []

            for sent in sentences:
                if session.state in (PlaybackState.CANCELLED, PlaybackState.ERROR):
                    break

                async for chunk in self.provider.stream(sent, self.current_voice_profile, is_ssml=is_ssml):
                    if session.state in (PlaybackState.CANCELLED, PlaybackState.ERROR):
                        break

                    chunk_latency = (time.perf_counter() - start_time) * 1000.0
                    if first_chunk:
                        first_chunk = False
                        self.metrics.record_first_audio_latency(chunk_latency)
                        # Emit SpeechPlaybackStarted
                        play_start_event = SpeechPlaybackStarted(
                            playback_id=session.playback_id,
                            voice_id=self.current_voice_profile.id,
                        )
                        self.event_bus.emit("SpeechPlaybackStarted", **play_start_event.__dict__)

                    all_chunks.append(chunk.data)

                    # Emit SpeechChunkGenerated
                    chunk_evt = SpeechChunkGenerated(
                        playback_id=session.playback_id,
                        chunk_id=chunk.chunk_id,
                        chunk_index=chunk.index,
                        is_final=chunk.is_final,
                        latency_ms=chunk_latency,
                    )
                    self.event_bus.emit("SpeechChunkGenerated", **chunk_evt.__dict__)

                    # Enqueue chunk into playback engine
                    await self.playback_engine.enqueue_chunk(chunk)

            # Record total synthesis metrics
            total_synth_latency = (time.perf_counter() - start_time) * 1000.0
            self.metrics.record_synthesis_latency(total_synth_latency)

            # Store in cache if enabled
            if self.cache and all_chunks:
                cache_key = AudioCache.generate_cache_key(text_or_ssml, self.current_voice_profile.id, self.provider.name)
                full_bytes = b"".join(all_chunks)
                cache_res = TTSResult(
                    session_id=session.playback_id,
                    provider=self.provider.name,
                    voice_profile=self.current_voice_profile,
                    latency_ms=total_synth_latency,
                    audio_duration_ms=len(full_bytes) * 5.0,
                    chunk_count=len(all_chunks),
                    audio_data=full_bytes,
                    success=True,
                )
                self.cache.put(cache_key, cache_res)

            session.duration_sec = (time.perf_counter() - start_time)
            self.metrics.record_audio_duration(session.duration_sec)

            # Emit SpeechPlaybackCompleted
            completed_evt = SpeechPlaybackCompleted(
                playback_id=session.playback_id,
                audio_duration_ms=session.duration_sec * 1000.0,
                total_chunks=session.audio_chunks_count,
            )
            self.event_bus.emit("SpeechPlaybackCompleted", **completed_evt.__dict__)

        except Exception as e:
            logger.error(f"[VoiceEngine] Error in synthesis loop for '{session.playback_id}': {e}")
            session.state = PlaybackState.ERROR
            self.metrics.total_errors += 1
            err_evt = SpeechPlaybackError(
                playback_id=session.playback_id,
                error_type=type(e).__name__,
                message=str(e),
            )
            self.event_bus.emit("SpeechPlaybackError", **err_evt.__dict__)

    async def pause(self) -> None:
        """Pauses active voice playback."""
        if self._active_session:
            await self.playback_engine.pause()
            pause_evt = SpeechPlaybackPaused(playback_id=self._active_session.playback_id)
            self.event_bus.emit("SpeechPlaybackPaused", **pause_evt.__dict__)

    async def resume(self) -> None:
        """Resumes paused voice playback."""
        if self._active_session:
            await self.playback_engine.resume()
            resume_evt = SpeechPlaybackResumed(playback_id=self._active_session.playback_id)
            self.event_bus.emit("SpeechPlaybackResumed", **resume_evt.__dict__)

    async def stop(self) -> None:
        """Stops voice playback cleanly."""
        if self._active_session:
            await self.playback_engine.stop()

    async def cancel(self) -> None:
        """Immediately interrupts voice playback and flushes queue."""
        if self._active_session:
            playback_id = self._active_session.playback_id
            await self.playback_engine.cancel()
            cancel_evt = SpeechPlaybackCancelled(playback_id=playback_id, reason="immediate_cancellation")
            self.event_bus.emit("SpeechPlaybackCancelled", **cancel_evt.__dict__)
            self._active_session = None


# Global singleton instance
voice_engine = VoiceEngine()
