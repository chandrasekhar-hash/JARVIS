"""
Abstract Base Classes & Interfaces for J.A.R.V.I.S. Phase V1.2 Speech Recognition Engine.
Provides strict provider-agnostic abstractions for audio sources, VAD engines, STT providers,
endpoint detectors, language classifiers, transcript buffers, cleaners, and recovery managers.
"""
from abc import ABC, abstractmethod
from typing import Optional, AsyncGenerator
from .models import (
    AudioFrame,
    VADResult,
    STTResult,
    LanguageResult,
    EndpointResult,
)


class IAudioSource(ABC):
    """Abstract interface for audio frame ingestion sources."""

    @abstractmethod
    async def start(self) -> None:
        """Starts audio ingestion."""
        pass

    @abstractmethod
    async def read_frame(self) -> Optional[AudioFrame]:
        """Reads a single PCM audio frame asynchronously."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stops audio ingestion and releases hardware/socket resources."""
        pass

    @abstractmethod
    def is_active(self) -> bool:
        """Returns True if the audio source is active and streaming."""
        pass


class IVADEngine(ABC):
    """Abstract interface for Voice Activity Detection engines."""

    @abstractmethod
    def process_frame(self, frame: AudioFrame) -> VADResult:
        """Processes an audio frame and returns VAD state."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Resets internal VAD state."""
        pass


class IStreamingSTTProvider(ABC):
    """Abstract interface for streaming Speech-to-Text providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Returns provider identification name."""
        pass

    @abstractmethod
    async def connect(self) -> None:
        """Establishes streaming session with STT provider engine."""
        pass

    @abstractmethod
    async def process_audio_chunk(self, chunk: bytes) -> STTResult:
        """Processes audio PCM chunk and returns intermediate partial transcription."""
        pass

    @abstractmethod
    async def finish_stream(self) -> STTResult:
        """Finalizes audio stream and returns the complete final transcription."""
        pass

    @abstractmethod
    async def reset(self) -> None:
        """Resets streaming STT provider context."""
        pass


class IEndpointDetector(ABC):
    """Abstract interface for intelligent end-of-speech detection."""

    @abstractmethod
    def evaluate(self, vad_result: VADResult, partial_transcript: str) -> EndpointResult:
        """Evaluates whether the speaker has completed their utterance."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Resets internal endpointing state."""
        pass


class ITranscriptBuffer(ABC):
    """Abstract interface for partial transcript accumulation and deduplication."""

    @abstractmethod
    def add_partial(self, text: str, confidence: float = 1.0) -> str:
        """Adds a partial transcript update, returning the stable deduplicated text."""
        pass

    @abstractmethod
    def finalize(self) -> str:
        """Finalizes transcript text and resets working buffers."""
        pass

    @abstractmethod
    def get_current_transcript(self) -> str:
        """Returns the current stable transcript string."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Resets transcript buffer state."""
        pass


class ILanguageDetector(ABC):
    """Abstract interface for spoken language classification."""

    @abstractmethod
    def detect_language(self, audio_bytes: bytes, text_sample: Optional[str] = None) -> LanguageResult:
        """Detects spoken language from audio or transcript text."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Resets language detector state."""
        pass


class ITranscriptCleaner(ABC):
    """Abstract interface for transcript cleanup and punctuation normalization."""

    @abstractmethod
    def clean(self, text: str) -> str:
        """Cleans, formats, and punctuates raw transcript text."""
        pass


class ISpeechRecoveryManager(ABC):
    """Abstract interface for automatic failure recovery."""

    @abstractmethod
    async def handle_error(self, error: Exception, session_id: str) -> bool:
        """Handles pipeline error and attempts automatic recovery. Returns True if recovered."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Resets recovery state metrics."""
        pass
