"""
Abstract Base Classes & Interfaces for J.A.R.V.I.S. Phase V1.6 Voice Orchestrator.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Callable
from .models import (
    SessionState,
    VoiceSession,
    ConversationTurn,
    OrchestratorResult,
)


class IStateMachine(ABC):
    """Abstract interface for Voice FSM State Machine."""

    @property
    @abstractmethod
    def current_state(self) -> SessionState:
        """Current state of the state machine."""
        pass

    @abstractmethod
    def transition_to(self, target_state: SessionState, reason: str = "") -> bool:
        """Transitions state machine to target state. Throws exception if transition is illegal."""
        pass

    @abstractmethod
    def can_transition_to(self, target_state: SessionState) -> bool:
        """Returns True if transition to target state is valid."""
        pass


class ISessionManager(ABC):
    """Abstract interface for Voice Session Manager."""

    @abstractmethod
    def create_session(self, user_id: str = "default_user", conversation_id: Optional[str] = None) -> VoiceSession:
        """Creates a new VoiceSession."""
        pass

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[VoiceSession]:
        """Retrieves session entity by session_id."""
        pass

    @abstractmethod
    def pause_session(self, session_id: str) -> bool:
        """Pauses target session."""
        pass

    @abstractmethod
    def resume_session(self, session_id: str) -> bool:
        """Resumes target session."""
        pass

    @abstractmethod
    def cancel_session(self, session_id: str, reason: str = "") -> bool:
        """Cancels target session."""
        pass

    @abstractmethod
    def destroy_session(self, session_id: str) -> bool:
        """Destroys target session."""
        pass


class IConversationHistory(ABC):
    """Abstract interface for Conversation History Manager."""

    @abstractmethod
    def add_turn(self, session_id: str, turn: ConversationTurn) -> None:
        """Appends turn to session history."""
        pass

    @abstractmethod
    def get_history(self, session_id: str) -> List[ConversationTurn]:
        """Returns turn history for session."""
        pass

    @abstractmethod
    def clear_history(self, session_id: str) -> None:
        """Clears turn history for session."""
        pass


class ILifecycleManager(ABC):
    """Abstract interface for Session Lifecycle Manager."""

    @abstractmethod
    async def start_session(self, user_id: str = "default_user") -> VoiceSession:
        """Launches a new voice interaction session."""
        pass

    @abstractmethod
    async def finish_session(self, session_id: str) -> bool:
        """Finishes target session cleanly."""
        pass

    @abstractmethod
    async def reset(self) -> None:
        """Resets orchestrator state."""
        pass


class IInterruptHandler(ABC):
    """Abstract interface for Barge-In Interrupt Handler."""

    @abstractmethod
    async def handle_barge_in(self, session_id: str) -> bool:
        """Handles user barge-in interruption during speech playback."""
        pass


class ITimeoutManager(ABC):
    """Abstract interface for Timeout Manager."""

    @abstractmethod
    def start_timeout(self, session_id: str, timeout_type: str, timeout_sec: float, callback: Callable) -> None:
        """Launches a timed watchdog monitor."""
        pass

    @abstractmethod
    def cancel_timeout(self, session_id: str, timeout_type: str) -> None:
        """Cancels active watchdog monitor."""
        pass


class IHealthMonitor(ABC):
    """Abstract interface for Subsystem Health Monitor."""

    @abstractmethod
    def is_healthy(self) -> bool:
        """Returns True if all subsystems are healthy."""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Returns status breakdown of all subsystems."""
        pass
