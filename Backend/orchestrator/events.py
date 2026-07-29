"""
Event payload definitions for J.A.R.V.I.S. Phase V1.6 Voice Orchestrator.
All events carry explicit session_id, conversation_id, turn_id, correlation_id, and timestamps.
"""
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SessionStarted:
    """Emitted when a new voice interaction session commences."""
    session_id: str
    conversation_id: str
    turn_id: Optional[str] = None
    correlation_id: str = ""
    user_id: str = "default_user"
    timestamp: float = field(default_factory=time.time)


@dataclass
class SessionCompleted:
    """Emitted when a voice interaction session completes cleanly."""
    session_id: str
    conversation_id: str
    turn_id: Optional[str] = None
    correlation_id: str = ""
    total_turns: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class SessionInterrupted:
    """Emitted when a user interrupts assistant playback (barge-in)."""
    session_id: str
    conversation_id: str
    turn_id: Optional[str] = None
    correlation_id: str = ""
    reason: str = "user_barge_in"
    timestamp: float = field(default_factory=time.time)


@dataclass
class SessionRecovered:
    """Emitted when a session recovers from an error or timeout condition."""
    session_id: str
    conversation_id: str
    turn_id: Optional[str] = None
    correlation_id: str = ""
    policy: str = "retry"
    timestamp: float = field(default_factory=time.time)


@dataclass
class SessionCancelled:
    """Emitted when a session is explicitly cancelled by user or command."""
    session_id: str
    conversation_id: str
    turn_id: Optional[str] = None
    correlation_id: str = ""
    reason: str = "user_cancellation"
    timestamp: float = field(default_factory=time.time)


@dataclass
class StateChanged:
    """Emitted whenever the session state machine transitions."""
    session_id: str
    conversation_id: str
    turn_id: Optional[str] = None
    correlation_id: str = ""
    from_state: str = ""
    to_state: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class OrchestratorError:
    """Emitted when an unhandled error occurs within the orchestrator lifecycle."""
    session_id: str
    conversation_id: str
    turn_id: Optional[str] = None
    correlation_id: str = ""
    error_type: str = ""
    message: str = ""
    timestamp: float = field(default_factory=time.time)
