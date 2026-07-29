"""
Data models and data structures for J.A.R.V.I.S. Phase V1.2 Speech Recognition Engine.
"""
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any


class SpeechState(str, Enum):
    """Execution state of the Speech Recognition Engine."""
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"


@dataclass
class AudioFrame:
    """Represents a discrete audio PCM frame ingested into the pipeline."""
    data: bytes
    sample_rate: int = 16000
    channels: int = 1
    timestamp: float = field(default_factory=time.time)
    session_id: str = ""
    frame_index: int = 0


@dataclass
class VADResult:
    """Output from Voice Activity Detection evaluation."""
    is_speech: bool
    confidence: float
    energy: float
    speech_duration_ms: float = 0.0
    speech_started: bool = False
    speech_ended: bool = False


@dataclass
class STTResult:
    """Output from Streaming STT transcription evaluation."""
    transcript: str
    is_final: bool
    confidence: float
    language: Optional[str] = None
    latency_ms: float = 0.0


@dataclass
class LanguageResult:
    """Output from spoken language classification."""
    language: str
    confidence: float
    is_fallback: bool = False


@dataclass
class EndpointResult:
    """Output from intelligent end-of-speech evaluation."""
    is_endpoint: bool
    pause_duration_ms: float
    confidence: float
    reason: str = "silence_timeout"


@dataclass
class SpeechSession:
    """Tracks state and metadata for an active speech recognition session."""
    session_id: str
    started_at: float = field(default_factory=time.time)
    language: str = "english"
    state: SpeechState = SpeechState.IDLE
    duration_sec: float = 0.0
    audio_frames_processed: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
