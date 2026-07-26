import time
import uuid
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


class PreferenceType(str, Enum):
    EXPLICIT = "explicit"
    IMPLICIT = "implicit"


class CommunicationStyle(str, Enum):
    CONCISE = "concise"
    DETAILED = "detailed"
    TECHNICAL = "technical"
    CASUAL = "casual"
    FORMAL = "formal"


class UserPreference(BaseModel):
    model_config = ConfigDict(frozen=False)

    preference_id: str = Field(default_factory=lambda: f"pref_{uuid.uuid4().hex[:12]}")
    user_id: str = Field(default="default_user", min_length=1)
    key: str = Field(min_length=1)
    value: Any
    category: str = Field(default="general")
    preference_type: PreferenceType = PreferenceType.EXPLICIT
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: str = Field(default="user_input")
    version: int = Field(default=1, ge=1)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v


class UserHabit(BaseModel):
    model_config = ConfigDict(frozen=False)

    habit_id: str = Field(default_factory=lambda: f"habit_{uuid.uuid4().hex[:12]}")
    habit_name: str = Field(min_length=1)
    category: str = Field(default="tool_usage")
    frequency_count: int = Field(default=1, ge=0)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    time_windows: List[str] = Field(default_factory=list)
    associated_tools: List[str] = Field(default_factory=list)
    last_observed_at: float = Field(default_factory=time.time)


class WorkflowAffinity(BaseModel):
    model_config = ConfigDict(frozen=True)

    workflow_pattern: str = Field(min_length=1)
    affinity_score: float = Field(default=0.5, ge=0.0, le=1.0)
    usage_count: int = Field(default=1, ge=0)
    preferred_tool_chain: List[str] = Field(default_factory=list)


class ActivityWindow(BaseModel):
    model_config = ConfigDict(frozen=True)

    day_of_week: int = Field(ge=0, le=6)  # 0=Monday, 6=Sunday
    start_hour: int = Field(ge=0, le=23)
    end_hour: int = Field(ge=0, le=23)
    activity_level: float = Field(default=0.5, ge=0.0, le=1.0)


class UserHabitProfile(BaseModel):
    model_config = ConfigDict(frozen=False)

    user_id: str = Field(default="default_user", min_length=1)
    habits: List[UserHabit] = Field(default_factory=list)
    activity_windows: List[ActivityWindow] = Field(default_factory=list)
    workflow_affinities: List[WorkflowAffinity] = Field(default_factory=list)
    top_tools: List[str] = Field(default_factory=list)
    last_analyzed_at: float = Field(default_factory=time.time)


class UserConsent(BaseModel):
    model_config = ConfigDict(frozen=False)

    user_id: str = Field(default="default_user", min_length=1)
    opt_in_personalization: bool = True
    implicit_learning_enabled: bool = True
    allow_tool_usage_tracking: bool = True
    allow_habit_analysis: bool = True
    updated_at: float = Field(default_factory=time.time)


class UserProfile(BaseModel):
    model_config = ConfigDict(frozen=False)

    user_id: str = Field(default="default_user", min_length=1)
    name: Optional[str] = None
    communication_style: CommunicationStyle = CommunicationStyle.CONCISE
    preferred_tools: Dict[str, float] = Field(default_factory=dict)
    explicit_preferences: Dict[str, Any] = Field(default_factory=dict)
    implicit_preferences: Dict[str, Any] = Field(default_factory=dict)
    habit_profile: UserHabitProfile = Field(default_factory=lambda: UserHabitProfile(user_id="default_user"))
    profile_version: int = Field(default=1, ge=1)
    updated_at: float = Field(default_factory=time.time)


class PreferenceObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: str = Field(default="default_user", min_length=1)
    observation_key: str = Field(min_length=1)
    observed_value: Any
    category: str = Field(default="general")
    context_tags: List[str] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)


class PreferenceUpdateResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    success: bool
    preference: Optional[UserPreference] = None
    was_merged: bool = False
    was_decayed: bool = False
    error_message: Optional[str] = None
