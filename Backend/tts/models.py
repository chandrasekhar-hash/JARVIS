"""
Data models and data structures for J.A.R.V.I.S. Phase V1.4 Voice Output Engine (TTS).
Includes VoiceProfile, AudioChunk, TTSResult, PlaybackState, and PlaybackSession.
"""
import time
import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


class PlaybackState(str, Enum):
    """Execution state lifecycle of a voice playback session."""
    IDLE = "IDLE"
    SYNTHESIZING = "SYNTHESIZING"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"


@dataclass
class VoiceProfile:
    """First-class Voice Profile metadata and capability descriptor."""
    id: str
    provider: str
    language: str = "english"
    gender: str = "female"
    name: str = "Default Voice"
    sample_rate: int = 24000
    supports_streaming: bool = True
    supports_ssml: bool = True
    supports_emotions: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AudioChunk:
    """Represents a discrete audio byte chunk synthesized by a TTS provider."""
    chunk_id: str = field(default_factory=lambda: f"chk_{uuid.uuid4().hex[:12]}")
    data: bytes = b""
    index: int = 0
    is_final: bool = False
    duration_ms: float = 0.0
    sample_rate: int = 24000
    format: str = "mp3"
    timestamp: float = field(default_factory=time.time)


@dataclass
class TTSResult:
    """Structured result returned by TTS synthesis operations."""
    session_id: str
    provider: str
    voice_profile: Optional[VoiceProfile] = None
    latency_ms: float = 0.0
    audio_duration_ms: float = 0.0
    cache_hit: bool = False
    chunk_count: int = 0
    audio_data: bytes = b""
    success: bool = True
    error: Optional[str] = None


@dataclass
class PlaybackSession:
    """Tracks state and metadata for an active TTS playback session."""
    playback_id: str = field(default_factory=lambda: f"pbk_{uuid.uuid4().hex[:12]}")
    conversation_turn_id: Optional[str] = None
    speech_session_id: Optional[str] = None
    started_at: float = field(default_factory=time.time)
    state: PlaybackState = PlaybackState.IDLE
    voice: Optional[VoiceProfile] = None
    provider: str = "mock"
    audio_chunks_count: int = 0
    duration_sec: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
