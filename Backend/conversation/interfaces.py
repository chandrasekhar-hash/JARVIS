from typing import Protocol, List, Optional, Dict, Any
from conversation.models import (
    ConversationSession,
    ConversationState,
    TopicTransition,
    ConversationReference,
    ConversationSummary,
    ContinuityValidation,
    ConversationResult,
)


class ISessionManager(Protocol):
    def create_session(self, user_id: str = "default_user") -> ConversationSession:
        ...

    def restore_session(self, session_id: str) -> Optional[ConversationSession]:
        ...

    def end_session(self, session_id: str) -> bool:
        ...


class ITopicManager(Protocol):
    def track_topic(self, turn_text: str, state: ConversationState) -> Optional[TopicTransition]:
        ...


class IContextTracker(Protocol):
    def resolve_references(
        self, turn_text: str, state: ConversationState
    ) -> List[ConversationReference]:
        ...

    def update_context(
        self, state: ConversationState, turn_text: str
    ) -> ConversationState:
        ...


class IContinuityValidator(Protocol):
    def validate_continuity(
        self, state: ConversationState, summary: ConversationSummary
    ) -> ContinuityValidation:
        ...


class IConversationContinuityEngine(Protocol):
    async def process_turn(
        self, session_id: str, turn_text: str, cognitive_context: Any = None
    ) -> ConversationResult:
        ...
