"""
Data models and state representations for J.A.R.V.I.S. Phase V1.6 Voice Orchestrator.
Includes SessionState enum, VoiceSession, ConversationTurn, SessionStatistics, OrchestratorResult, and LifecycleEvent.
"""
import time
import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


class SessionState(str, Enum):
    """Finite State Machine execution lifecycle states for voice interaction sessions."""
    IDLE = "IDLE"
    AWAITING_WAKE_WORD = "AWAITING_WAKE_WORD"
    LISTENING = "LISTENING"
    PROCESSING_AUDIO = "PROCESSING_AUDIO"
    TRANSCRIBING = "TRANSCRIBING"
    THINKING = "THINKING"
    PREPARING_RESPONSE = "PREPARING_RESPONSE"
    SPEAKING = "SPEAKING"
    WAITING_FOR_USER = "WAITING_FOR_USER"
    INTERRUPTED = "INTERRUPTED"
    PAUSED = "PAUSED"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"
    RECOVERING = "RECOVERING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


@dataclass
class ConversationTurn:
    """Represents a single turn in a multi-turn voice interaction session."""
    turn_id: str = field(default_factory=lambda: f"trn_{uuid.uuid4().hex[:12]}")
    session_id: str = ""
    user_text: str = ""
    assistant_text: str = ""
    state: str = "COMPLETED"
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    turn_latency_ms: float = 0.0


@dataclass
class SessionStatistics:
    """Quantitative session metrics accumulator."""
    turns_count: int = 0
    total_duration_sec: float = 0.0
    recognition_latency_ms: float = 0.0
    thinking_latency_ms: float = 0.0
    speaking_latency_ms: float = 0.0
    barge_in_count: int = 0
    cancellation_count: int = 0
    recovery_count: int = 0
    timeout_count: int = 0


@dataclass
class VoiceSession:
    """Primary Voice Session entity tracking lifecycle state and history."""
    session_id: str = field(default_factory=lambda: f"ses_{uuid.uuid4().hex[:12]}")
    user_id: str = "default_user"
    conversation_id: str = field(default_factory=lambda: f"cnv_{uuid.uuid4().hex[:12]}")
    correlation_id: str = field(default_factory=lambda: f"cor_{uuid.uuid4().hex[:12]}")
    started_at: float = field(default_factory=time.time)
    state: SessionState = SessionState.IDLE
    turns: List[ConversationTurn] = field(default_factory=list)
    statistics: SessionStatistics = field(default_factory=SessionStatistics)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestratorResult:
    """Output result returned by Orchestrator operations."""
    success: bool = True
    session_id: str = ""
    state: SessionState = SessionState.IDLE
    current_turn: Optional[ConversationTurn] = None
    error: Optional[str] = None


@dataclass
class LifecycleEvent:
    """Event representation of lifecycle state transitions."""
    event_id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    session_id: str = ""
    state: SessionState = SessionState.IDLE
    timestamp: float = field(default_factory=time.time)
