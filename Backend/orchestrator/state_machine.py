"""
Finite State Machine Engine for J.A.R.V.I.S. Phase V1.6 Voice Orchestrator.
Validates state transitions across the full voice interaction lifecycle.
Illegal transitions raise InvalidStateTransitionError.
"""
import logging
from typing import Set, Dict
from .models import SessionState
from .interfaces import IStateMachine

logger = logging.getLogger("JARVIS_VoiceStateMachine")


class InvalidStateTransitionError(Exception):
    """Exception raised when an invalid or illegal state machine transition is attempted."""
    pass


class VoiceStateMachine(IStateMachine):
    """
    Finite State Machine governing voice session lifecycle.
    """

    # Allowed state transition map
    VALID_TRANSITIONS: Dict[SessionState, Set[SessionState]] = {
        SessionState.IDLE: {
            SessionState.AWAITING_WAKE_WORD,
            SessionState.LISTENING,
            SessionState.CANCELLING,
            SessionState.ERROR,
        },
        SessionState.AWAITING_WAKE_WORD: {
            SessionState.LISTENING,
            SessionState.IDLE,
            SessionState.CANCELLING,
            SessionState.ERROR,
        },
        SessionState.LISTENING: {
            SessionState.PROCESSING_AUDIO,
            SessionState.PAUSED,
            SessionState.INTERRUPTED,
            SessionState.CANCELLING,
            SessionState.ERROR,
        },
        SessionState.PROCESSING_AUDIO: {
            SessionState.TRANSCRIBING,
            SessionState.LISTENING,
            SessionState.CANCELLING,
            SessionState.ERROR,
        },
        SessionState.TRANSCRIBING: {
            SessionState.THINKING,
            SessionState.LISTENING,
            SessionState.CANCELLING,
            SessionState.ERROR,
        },
        SessionState.THINKING: {
            SessionState.PREPARING_RESPONSE,
            SessionState.CANCELLING,
            SessionState.ERROR,
        },
        SessionState.PREPARING_RESPONSE: {
            SessionState.SPEAKING,
            SessionState.CANCELLING,
            SessionState.ERROR,
        },
        SessionState.SPEAKING: {
            SessionState.WAITING_FOR_USER,
            SessionState.INTERRUPTED,
            SessionState.COMPLETED,
            SessionState.CANCELLING,
            SessionState.ERROR,
        },
        SessionState.WAITING_FOR_USER: {
            SessionState.LISTENING,
            SessionState.COMPLETED,
            SessionState.IDLE,
            SessionState.PAUSED,
            SessionState.CANCELLING,
            SessionState.ERROR,
        },
        SessionState.INTERRUPTED: {
            SessionState.LISTENING,
            SessionState.IDLE,
            SessionState.CANCELLING,
            SessionState.ERROR,
        },
        SessionState.PAUSED: {
            SessionState.LISTENING,
            SessionState.SPEAKING,
            SessionState.IDLE,
            SessionState.CANCELLING,
        },
        SessionState.CANCELLING: {
            SessionState.CANCELLED,
            SessionState.COMPLETED,
            SessionState.IDLE,
            SessionState.ERROR,
        },
        SessionState.CANCELLED: {
            SessionState.COMPLETED,
            SessionState.IDLE,
        },
        SessionState.RECOVERING: {
            SessionState.LISTENING,
            SessionState.IDLE,
            SessionState.ERROR,
        },
        SessionState.ERROR: {
            SessionState.RECOVERING,
            SessionState.IDLE,
            SessionState.COMPLETED,
        },
        SessionState.COMPLETED: {
            SessionState.IDLE,
            SessionState.LISTENING,
            SessionState.AWAITING_WAKE_WORD,
        },
    }

    def __init__(self, initial_state: SessionState = SessionState.IDLE):
        self._current_state: SessionState = initial_state

    @property
    def current_state(self) -> SessionState:
        return self._current_state

    def can_transition_to(self, target_state: SessionState) -> bool:
        """Returns True if transition from current state to target state is allowed."""
        allowed = self.VALID_TRANSITIONS.get(self._current_state, set())
        return target_state in allowed

    def transition_to(self, target_state: SessionState, reason: str = "") -> bool:
        """
        Transitions to target state if valid.
        Raises InvalidStateTransitionError if transition is illegal.
        """
        if self._current_state == target_state:
            return True

        if not self.can_transition_to(target_state):
            err_msg = (
                f"[StateMachine] Illegal state transition attempt from "
                f"'{self._current_state.value}' -> '{target_state.value}' (Reason: {reason or 'none'})"
            )
            logger.error(err_msg)
            raise InvalidStateTransitionError(err_msg)

        logger.info(f"[StateMachine] Transitioned: '{self._current_state.value}' -> '{target_state.value}' ({reason})")
        self._current_state = target_state
        return True
