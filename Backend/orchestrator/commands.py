"""
Explicit Command Definitions for J.A.R.V.I.S. Phase V1.6 Voice Orchestrator.
Encapsulates intent separately from event dispatches.
Command -> Coordinator -> Subsystems -> Events.
"""
import uuid
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StartSessionCommand:
    """Command to initiate a new voice session."""
    user_id: str = "default_user"
    conversation_id: Optional[str] = None
    correlation_id: str = field(default_factory=lambda: f"cor_{uuid.uuid4().hex[:12]}")
    timestamp: float = field(default_factory=time.time)


@dataclass
class CancelSessionCommand:
    """Command to cancel an active voice session."""
    session_id: str
    reason: str = "user_command"
    timestamp: float = field(default_factory=time.time)


@dataclass
class PauseConversationCommand:
    """Command to pause an active conversation session."""
    session_id: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class ResumeConversationCommand:
    """Command to resume a paused conversation session."""
    session_id: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class StopSpeakingCommand:
    """Command to immediately halt assistant voice output playback."""
    session_id: str
    reason: str = "user_barge_in"
    timestamp: float = field(default_factory=time.time)


@dataclass
class ResetSessionCommand:
    """Command to reset orchestrator state and clear active sessions."""
    session_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
