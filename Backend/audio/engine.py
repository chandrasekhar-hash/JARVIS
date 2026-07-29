"""
Master Audio Intelligence Engine Orchestrator for J.A.R.V.I.S. Phase V1.5.
Coordinates AudioConfig, AudioProcessingPipeline, AudioSession, and EventBus dispatches.
"""
import uuid
import time
import inspect
import asyncio
import logging
from typing import Optional, Dict, Any, List, AsyncGenerator

from .config import AudioConfig, audio_config
from .models import (
    AudioFrame,
    EnhancedAudioFrame,
    AudioQualityReport,
    AudioConfidence,
    AudioSession,
    ProcessingResult,
)
from .pipeline import AudioProcessingPipeline
from .metrics import audio_metrics, AudioMetrics
from brain.event_bus import event_bus, EventBus

logger = logging.getLogger("JARVIS_AudioIntelligenceEngine")


class AudioIntelligenceEngine:
    """
    Production-grade Audio Intelligence Engine providing pre-STT audio enhancement,
    noise suppression, echo cancellation, gain normalization, and quality scoring.
    """

    def __init__(
        self,
        config: Optional[AudioConfig] = None,
        pipeline: Optional[AudioProcessingPipeline] = None,
        bus: Optional[EventBus] = None,
    ):
        self.config = config or audio_config
        self.event_bus = bus or event_bus
        self.pipeline = pipeline or AudioProcessingPipeline(config=self.config, bus=self.event_bus)
        self.metrics = audio_metrics

        self._active_session: Optional[AudioSession] = None
        self._subscribe_events()

    def _subscribe_events(self) -> None:
        """Subscribes to incoming AudioInputReceived events from input drivers."""
        try:
            self.event_bus.subscribe("AudioInputReceived", self._handle_audio_input_event)
        except Exception as e:
            logger.warning(f"[AudioIntelligenceEngine] Could not subscribe to AudioInputReceived event: {e}")

    def _handle_audio_input_event(self, event: Any = None, **kwargs) -> None:
        """Handles incoming AudioInputReceived event over EventBus."""
        data = event.data if hasattr(event, "data") else (event if isinstance(event, dict) else kwargs)
        pcm_bytes = data.get("data") if isinstance(data, dict) else None
        session_id = (data.get("session_id") if isinstance(data, dict) else None) or "default_session"

        if not pcm_bytes:
            return

        frame = AudioFrame(
            data=pcm_bytes,
            sample_rate=data.get("sample_rate", self.config.sample_rate),
            channels=data.get("channels", 1),
        )

        if inspect.iscoroutinefunction(self.process_frame):
            asyncio.create_task(self.process_frame(frame, session_id=session_id))
        else:
            asyncio.run(self.process_frame(frame, session_id=session_id))

    def set_pipeline(self, pipeline: AudioProcessingPipeline) -> None:
        """Updates active processing pipeline dynamically."""
        self.pipeline = pipeline

    def get_metrics(self) -> Dict[str, Any]:
        """Returns snapshot summary of audio metrics telemetry."""
        return self.metrics.get_summary()

    def start_session(self) -> AudioSession:
        """Launches a new AudioSession tracking quality reports."""
        session = AudioSession()
        self._active_session = session
        return session

    def get_active_session(self) -> Optional[AudioSession]:
        """Returns active audio session."""
        return self._active_session

    async def process_frame(self, frame: AudioFrame, session_id: str = "default_session") -> ProcessingResult:
        """Processes a single AudioFrame through the audio intelligence pipeline."""
        res = await self.pipeline.process_frame(frame, session_id=session_id)
        if res.quality_report and self._active_session:
            self._active_session.frames_count += 1
            self._active_session.quality_reports.append(res.quality_report)
        return res

    async def process_stream(
        self,
        stream: AsyncGenerator[AudioFrame, None],
        session_id: str = "default_session",
    ) -> AsyncGenerator[ProcessingResult, None]:
        """Processes a continuous stream of AudioFrames asynchronously."""
        async for frame in stream:
            res = await self.process_frame(frame, session_id=session_id)
            yield res


# Global singleton instance
audio_engine = AudioIntelligenceEngine()
