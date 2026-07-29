"""
Data models and data structures for J.A.R.V.I.S. Phase V1.3 Conversation Engine.
Includes session models, topic transitions, reference resolutions, conversation turns,
state definitions, summaries, continuity metrics, and results.
"""
import time
import uuid
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class TurnState(str, Enum):
    """Execution state of an individual conversation turn."""
    STARTED = "STARTED"
    THINKING = "THINKING"
    RESPONDING = "RESPONDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"


class IntentType(str, Enum):
    """Classified intent of a user conversation turn."""
    QUESTION = "QUESTION"
    COMMAND = "COMMAND"
    FOLLOW_UP = "FOLLOW_UP"
    CLARIFICATION = "CLARIFICATION"
    CONTINUATION = "CONTINUATION"


class IntentResult(BaseModel):
    """Output from intent classification."""
    model_config = ConfigDict(frozen=True)

    intent: IntentType = IntentType.QUESTION
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    entities: Dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(default="keyword_heuristic")


class ConversationTurn(BaseModel):
    """Represents an individual atomic turn within a conversation session."""
    model_config = ConfigDict(frozen=False)

    turn_id: str = Field(default_factory=lambda: f"trn_{uuid.uuid4().hex[:12]}")
    session_id: str = Field(min_length=1)
    parent_turn_id: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    user_text: str = Field(min_length=1)
    assistant_response: Optional[str] = None
    intent: Optional[IntentResult] = None
    state: TurnState = TurnState.STARTED
    response_time_ms: float = Field(default=0.0, ge=0.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ConversationSession(BaseModel):
    model_config = ConfigDict(frozen=False)

    session_id: str = Field(default_factory=lambda: f"sess_{uuid.uuid4().hex[:12]}")
    user_id: str = Field(default="default_user", min_length=1)
    is_active: bool = True
    created_at: float = Field(default_factory=time.time)
    last_active_at: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Topic(BaseModel):
    model_config = ConfigDict(frozen=True)

    topic_id: str = Field(default_factory=lambda: f"top_{uuid.uuid4().hex[:12]}")
    topic_name: str = Field(min_length=1)
    subtopics: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    started_at: float = Field(default_factory=time.time)


class TopicTransition(BaseModel):
    model_config = ConfigDict(frozen=True)

    from_topic: Optional[str] = None
    to_topic: str = Field(min_length=1)
    reason: str = Field(default="topic_shift")
    timestamp: float = Field(default_factory=time.time)


class ConversationReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    expression: str = Field(min_length=1)
    resolved_target: str = Field(min_length=1)
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    timestamp: float = Field(default_factory=time.time)


class ConversationState(BaseModel):
    model_config = ConfigDict(frozen=False)

    session_id: str = Field(min_length=1)
    active_topic: Optional[Topic] = None
    topic_history: List[TopicTransition] = Field(default_factory=list)
    resolved_references: Dict[str, str] = Field(default_factory=dict)
    last_turn_text: Optional[str] = None
    last_target_object: Optional[str] = None
    turn_count: int = Field(default=0, ge=0)
    history: List[ConversationTurn] = Field(default_factory=list)
    updated_at: float = Field(default_factory=time.time)


class ConversationSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    summary_id: str = Field(default_factory=lambda: f"sum_{uuid.uuid4().hex[:12]}")
    short_summary: str = Field(min_length=1)
    working_summary: str = Field(min_length=1)
    long_term_summary: str = Field(min_length=1)
    timestamp: float = Field(default_factory=time.time)


class ContinuityMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_restore_time_ms: float = Field(default=0.0, ge=0.0)
    reference_resolution_time_ms: float = Field(default=0.0, ge=0.0)
    topic_tracking_time_ms: float = Field(default=0.0, ge=0.0)
    pipeline_time_ms: float = Field(default=0.0, ge=0.0)
    timestamp: float = Field(default_factory=time.time)


class ContinuityValidation(BaseModel):
    model_config = ConfigDict(frozen=True)

    is_consistent: bool = True
    topic_consistency_score: float = Field(default=1.0, ge=0.0, le=1.0)
    reference_validity_score: float = Field(default=1.0, ge=0.0, le=1.0)
    session_integrity: bool = True
    coherence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    issues: List[str] = Field(default_factory=list)


class ConversationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    success: bool
    session: Optional[ConversationSession] = None
    state: Optional[ConversationState] = None
    current_turn: Optional[ConversationTurn] = None
    assistant_response: Optional[str] = None
    resolved_references: List[ConversationReference] = Field(default_factory=list)
    summary: Optional[ConversationSummary] = None
    validation: Optional[ContinuityValidation] = None
    metrics: ContinuityMetrics = Field(default_factory=ContinuityMetrics)
    error_message: Optional[str] = None
