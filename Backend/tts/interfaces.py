"""
Abstract Base Classes & Interfaces for J.A.R.V.I.S. Phase V1.4 Voice Output Engine (TTS).
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, AsyncGenerator
from .models import (
    AudioChunk,
    TTSResult,
    VoiceProfile,
    PlaybackSession,
)


class ITextPreprocessor(ABC):
    """Abstract interface for text pre-synthesis normalization."""

    @abstractmethod
    def preprocess(self, text: str) -> str:
        """Preprocesses text for natural speech pronunciation."""
        pass


class ISentenceSegmenter(ABC):
    """Abstract interface for text sentence boundary segmentation."""

    @abstractmethod
    def segment(self, text: str) -> List[str]:
        """Segments response text into streaming sentence chunks."""
        pass


class ITTSProvider(ABC):
    """Abstract interface for streaming Text-to-Speech providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Returns provider identification name."""
        pass

    @abstractmethod
    async def connect(self) -> None:
        """Connects to provider engine session."""
        pass

    @abstractmethod
    async def synthesize(
        self,
        text_or_ssml: str,
        voice: VoiceProfile,
        is_ssml: bool = False,
    ) -> TTSResult:
        """Synthesizes text/SSML into full audio bytes."""
        pass

    @abstractmethod
    async def stream(
        self,
        text_or_ssml: str,
        voice: VoiceProfile,
        is_ssml: bool = False,
    ) -> AsyncGenerator[AudioChunk, None]:
        """Streams synthesized audio chunks asynchronously."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stops active synthesis."""
        pass

    @abstractmethod
    async def cancel(self) -> None:
        """Immediately cancels synthesis."""
        pass

    @abstractmethod
    async def reset(self) -> None:
        """Resets provider context."""
        pass


class IAudioOutput(ABC):
    """Abstract interface for audio playback output drivers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Returns output driver name."""
        pass

    @abstractmethod
    async def start(self) -> None:
        """Initializes output device/socket."""
        pass

    @abstractmethod
    async def play_chunk(self, chunk: AudioChunk) -> None:
        """Plays or dispatches audio chunk."""
        pass

    @abstractmethod
    async def pause(self) -> None:
        """Pauses audio output driver."""
        pass

    @abstractmethod
    async def resume(self) -> None:
        """Resumes audio output driver."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stops audio output driver cleanly."""
        pass

    @abstractmethod
    async def cancel(self) -> None:
        """Immediately cancels playback."""
        pass

    @abstractmethod
    def is_active(self) -> bool:
        """Returns True if output driver is active."""
        pass


class IAudioCache(ABC):
    """Abstract interface for in-memory LRU audio caching."""

    @abstractmethod
    def get(self, key: str) -> Optional[TTSResult]:
        """Retrieves cached TTSResult by key."""
        pass

    @abstractmethod
    def put(self, key: str, result: TTSResult) -> None:
        """Stores TTSResult in cache."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clears cached entries."""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Returns cache hit/miss statistics."""
        pass


class IPlaybackEngine(ABC):
    """Abstract interface for audio playback queue management."""

    @abstractmethod
    async def enqueue_chunk(self, chunk: AudioChunk) -> None:
        """Enqueues audio chunk for playback."""
        pass

    @abstractmethod
    async def start_playback(self, session: PlaybackSession) -> None:
        """Launches playback processing loop."""
        pass

    @abstractmethod
    async def pause(self) -> None:
        """Pauses active playback queue."""
        pass

    @abstractmethod
    async def resume(self) -> None:
        """Resumes active playback queue."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stops playback queue cleanly."""
        pass

    @abstractmethod
    async def cancel(self) -> None:
        """Immediately cancels playback queue."""
        pass
