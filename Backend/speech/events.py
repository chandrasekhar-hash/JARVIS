"""
Event payload definitions for J.A.R.V.I.S. Phase V1.2 Speech Recognition Engine.
All events carry explicit session_id, timestamp, and confidence values.
"""
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SpeechStartedEvent:
    """Emitted when Voice Activity Detection detects the start of user speech."""
    session_id: str
    confidence: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class SpeechPartialEvent:
    """Emitted when Streaming STT produces an intermediate partial transcript update."""
    session_id: str
    transcript: str
    confidence: float
    language: str
    latency_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class SpeechFinalEvent:
    """Emitted when user speech finishes and the final clean transcript is ready."""
    session_id: str
    transcript: str
    confidence: float
    language: str
    duration_sec: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class SpeechEndedEvent:
    """Emitted when Voice Activity Detection / Endpoint Detector confirms end of speech."""
    session_id: str
    duration_sec: float
    endpoint_reason: str
    confidence: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class SpeechCancelledEvent:
    """Emitted when speech processing is explicitly interrupted or cancelled."""
    session_id: str
    reason: str = "user_cancellation"
    timestamp: float = field(default_factory=time.time)


@dataclass
class SpeechErrorEvent:
    """Emitted when a recoverable or fatal error occurs during speech processing."""
    session_id: str
    error_type: str
    message: str
    recovered: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class LanguageDetectedEvent:
    """Emitted when spoken language classification resolves."""
    session_id: str
    language: str
    confidence: float
    is_fallback: bool = False
    timestamp: float = field(default_factory=time.time)
