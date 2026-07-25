import time
import uuid
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


class StrategyType(str, Enum):
    DIRECT_EXECUTION = "direct_execution"
    HIERARCHICAL_DECOMPOSITION = "hierarchical_decomposition"
    EXPLORATORY_SEARCH = "exploratory_search"
    FEASIBILITY_PROBING = "feasibility_probing"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GoalOutcome(str, Enum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PolicyViolationType(str, Enum):
    LOW_CONFIDENCE = "low_confidence"
    UNSAFE_TIER = "unsafe_tier"
    PATH_RESTRICTION = "path_restriction"
    RESOURCE_LIMIT_EXCEEDED = "resource_limit_exceeded"
    EXCEEDED_MAX_DEPTH = "exceeded_max_depth"
    INVALID_GOAL_SCHEMA = "invalid_goal_schema"


class StrategyRecommendation(BaseModel):
    model_config = ConfigDict(frozen=True)

    strategy: StrategyType
    rationale: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


class CognitiveAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    assessment_id: str = Field(default_factory=lambda: f"cog_assess_{uuid.uuid4().hex[:12]}")
    goal_id: str = Field(min_length=1)
    confidence_score: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel
    recommended_strategy: StrategyType
    matched_experience_ids: List[str] = Field(default_factory=list)
    reasoning_summary: str = Field(min_length=1)
    approved: bool = True
    alternative_strategies: List[StrategyType] = Field(default_factory=list)
    estimated_complexity: float = Field(default=5.0, ge=1.0, le=10.0)
    estimated_success_probability: float = Field(default=0.8, ge=0.0, le=1.0)
    created_at: float = Field(default_factory=time.time)

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("confidence_score must be between 0.0 and 1.0")
        return v


class ReflectionReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    reflection_id: str = Field(default_factory=lambda: f"refl_{uuid.uuid4().hex[:12]}")
    goal_id: str = Field(min_length=1)
    workflow_id: str = Field(min_length=1)
    outcome: GoalOutcome
    total_execution_time_sec: float = Field(ge=0.0)
    tool_effectiveness_scores: Dict[str, float] = Field(default_factory=dict)
    lessons_learned: List[str] = Field(default_factory=list)
    success_factors: List[str] = Field(default_factory=list)
    failure_causes: List[str] = Field(default_factory=list)
    identified_bottlenecks: List[str] = Field(default_factory=list)
    recommended_improvements: List[str] = Field(default_factory=list)
    confidence_adjustment: float = Field(default=0.0, ge=-1.0, le=1.0)
    execution_statistics: Dict[str, Any] = Field(default_factory=dict)
    linked_experiences: List[str] = Field(default_factory=list)
    suggested_template_id: Optional[str] = None
    created_at: float = Field(default_factory=time.time)


class WorkflowTemplate(BaseModel):
    model_config = ConfigDict(frozen=True)

    template_id: str = Field(default_factory=lambda: f"tmpl_{uuid.uuid4().hex[:12]}")
    goal_pattern: str = Field(min_length=1)
    recommended_tasks: List[Dict[str, Any]] = Field(default_factory=list)
    success_count: int = Field(default=1, ge=0)
    average_duration_sec: float = Field(default=0.0, ge=0.0)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class FailurePattern(BaseModel):
    model_config = ConfigDict(frozen=True)

    pattern_id: str = Field(default_factory=lambda: f"fail_pat_{uuid.uuid4().hex[:12]}")
    error_signature: str = Field(min_length=1)
    root_cause: str = Field(min_length=1)
    suggested_workaround: str = Field(min_length=1)
    occurrence_count: int = Field(default=1, ge=1)
    last_seen_at: float = Field(default_factory=time.time)


class PolicyValidationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    is_valid: bool
    risk_level: RiskLevel = RiskLevel.LOW
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    approved_strategy: Optional[StrategyType] = None
    violations: List[str] = Field(default_factory=list)
    violation_type: Optional[PolicyViolationType] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class AdaptationPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    plan_id: str = Field(default_factory=lambda: f"adapt_{uuid.uuid4().hex[:12]}")
    goal_id: str = Field(min_length=1)
    adapted_strategy: StrategyType
    recommended_task_order: List[str] = Field(default_factory=list)
    decomposition_changes: List[Dict[str, Any]] = Field(default_factory=list)
    retry_policy: Dict[str, Any] = Field(default_factory=dict)
    parallelisation_recommendations: List[str] = Field(default_factory=list)
    resource_recommendations: List[str] = Field(default_factory=list)
    estimated_improvement: float = Field(default=0.15, ge=0.0, le=1.0)
    adaptation_summary: str = Field(min_length=1)
    approved: bool = True
    created_at: float = Field(default_factory=time.time)


class GoalExecutionPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    plan_id: str = Field(default_factory=lambda: f"gep_{uuid.uuid4().hex[:12]}")
    ordered_goals: List[str] = Field(default_factory=list)
    priority_scores: Dict[str, float] = Field(default_factory=dict)
    dependency_graph: Dict[str, List[str]] = Field(default_factory=dict)
    execution_batches: List[List[str]] = Field(default_factory=list)
    blocked_goals: List[str] = Field(default_factory=list)
    resource_allocations: Dict[str, List[str]] = Field(default_factory=list)
    estimated_completion_order: List[str] = Field(default_factory=list)
    coordination_summary: str = Field(min_length=1)
    approved: bool = True
    created_at: float = Field(default_factory=time.time)
