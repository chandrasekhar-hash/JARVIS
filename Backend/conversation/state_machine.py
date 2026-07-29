"""
Conversation State Machine for J.A.R.V.I.S. Phase V1.3 Conversation Engine.
Manages transition lifecycle: IDLE -> LISTENING -> THINKING -> RESPONDING -> WAITING -> IDLE.
"""
from enum import Enum
from typing import Dict, Set, Optional


class ConversationStateEnum(str, Enum):
    """Dialogue turn execution state lifecycle."""
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    RESPONDING = "RESPONDING"
    WAITING = "WAITING"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"


class ConversationStateMachine:
    """
    Validates and manages state machine transitions for conversation turns.
    Prevents invalid or out-of-order state mutations.
    """

    ALLOWED_TRANSITIONS: Dict[ConversationStateEnum, Set[ConversationStateEnum]] = {
        ConversationStateEnum.IDLE: {
            ConversationStateEnum.LISTENING,
            ConversationStateEnum.THINKING,
            ConversationStateEnum.CANCELLED,
            ConversationStateEnum.ERROR,
        },
        ConversationStateEnum.LISTENING: {
            ConversationStateEnum.THINKING,
            ConversationStateEnum.CANCELLED,
            ConversationStateEnum.ERROR,
        },
        ConversationStateEnum.THINKING: {
            ConversationStateEnum.RESPONDING,
            ConversationStateEnum.CANCELLED,
            ConversationStateEnum.ERROR,
        },
        ConversationStateEnum.RESPONDING: {
            ConversationStateEnum.WAITING,
            ConversationStateEnum.IDLE,
            ConversationStateEnum.CANCELLED,
            ConversationStateEnum.ERROR,
        },
        ConversationStateEnum.WAITING: {
            ConversationStateEnum.LISTENING,
            ConversationStateEnum.THINKING,
            ConversationStateEnum.IDLE,
            ConversationStateEnum.CANCELLED,
            ConversationStateEnum.ERROR,
        },
        ConversationStateEnum.CANCELLED: {
            ConversationStateEnum.IDLE,
            ConversationStateEnum.LISTENING,
        },
        ConversationStateEnum.ERROR: {
            ConversationStateEnum.IDLE,
            ConversationStateEnum.LISTENING,
        },
    }

    def __init__(self, initial_state: ConversationStateEnum = ConversationStateEnum.IDLE):
        self._current_state: ConversationStateEnum = initial_state

    @property
    def current_state(self) -> ConversationStateEnum:
        return self._current_state

    def transition_to(self, target_state: ConversationStateEnum) -> bool:
        """Transitions state if allowed by state machine rules."""
        allowed = self.ALLOWED_TRANSITIONS.get(self._current_state, set())
        if target_state in allowed or target_state == self._current_state:
            self._current_state = target_state
            return True
        return False

    def reset() -> None:
        self._current_state = ConversationStateEnum.IDLE
