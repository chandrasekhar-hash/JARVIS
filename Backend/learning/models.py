import time
import uuid
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


class LearningFeedback(BaseModel):
    model_config = ConfigDict(frozen=True)

    execution_id: str = Field(default_factory=lambda: f"exec_{uuid.uuid4().hex[:12]}")
    goal_id: str = ""
    strategy_id: str = ""
    success: bool
    duration_sec: float = Field(default=0.0, ge=0.0)
    retry_count: int = Field(default=0, ge=0)
    user_rating: Optional[float] = Field(default=None, ge=-1.0, le=1.0)
    policy_violations: List[str] = Field(default_factory=list)
    reflection_report: Optional[Dict[str, Any]] = None
    failure_severity: float = Field(default=0.0, ge=0.0, le=1.0)
    context_id: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)

    @field_validator("user_rating")
    @classmethod
    def validate_user_rating(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (-1.0 <= v <= 1.0):
            raise ValueError("user_rating must be between -1.0 and +1.0")
        return v


class RewardSignal(BaseModel):
    model_config = ConfigDict(frozen=True)

    reward_id: str = Field(default_factory=lambda: f"rwd_{uuid.uuid4().hex[:12]}")
    execution_id: str = Field(min_length=1)
    goal_id: str = Field(min_length=1)
    strategy_id: str = Field(min_length=1)
    base_score: float
    duration_penalty: float = Field(default=0.0, ge=0.0)
    retry_penalty: float = Field(default=0.0, ge=0.0)
    rating_boost: float = Field(default=0.0)
    violation_penalty: float = Field(default=0.0, ge=0.0)
    reflection_score: float = Field(default=0.0)
    severity_penalty: float = Field(default=0.0, ge=0.0)
    final_reward: float = Field(ge=-1.0, le=1.0)
    timestamp: float = Field(default_factory=time.time)

    @field_validator("final_reward")
    @classmethod
    def validate_final_reward(cls, v: float) -> float:
        if not (-1.0 <= v <= 1.0):
            raise ValueError("final_reward must be strictly between -1.0 and +1.0")
        return v


class CalibrationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    calibration_id: str = Field(default_factory=lambda: f"cal_{uuid.uuid4().hex[:12]}")
    strategy_id: str = Field(min_length=1)
    prior_confidence: float = Field(ge=0.0, le=1.0)
    calibrated_confidence: float = Field(ge=0.0, le=1.0)
    calibration_delta: float
    reward_score: float = Field(ge=-1.0, le=1.0)
    samples_count: int = Field(ge=0)
    moving_average: float = Field(ge=-1.0, le=1.0)
    decay_applied: float = Field(default=0.0, ge=0.0)
    boost_applied: float = Field(default=0.0, ge=0.0)
    timestamp: float = Field(default_factory=time.time)


class StrategyLearningRecord(BaseModel):
    model_config = ConfigDict(frozen=False)

    strategy_id: str = Field(min_length=1)
    strategy_type: Optional[str] = None
    ranking_weight: float = Field(default=1.0, ge=0.0, le=10.0)
    historical_success_score: float = Field(default=0.5, ge=0.0, le=1.0)
    reuse_score: float = Field(default=0.0, ge=0.0)
    confidence_metric: float = Field(default=0.5, ge=0.0, le=1.0)
    total_trials: int = Field(default=0, ge=0)
    success_count: int = Field(default=0, ge=0)
    failure_count: int = Field(default=0, ge=0)
    recent_rewards: List[float] = Field(default_factory=list)
    last_updated_at: float = Field(default_factory=time.time)


class LearningMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    metrics_id: str = Field(default_factory=lambda: f"lm_{uuid.uuid4().hex[:12]}")
    total_feedbacks_processed: int = Field(default=0, ge=0)
    successful_learnings: int = Field(default=0, ge=0)
    failed_learnings: int = Field(default=0, ge=0)
    average_reward: float = Field(default=0.0, ge=-1.0, le=1.0)
    average_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    last_learning_timestamp: float = Field(default_factory=time.time)
    strategy_records_count: int = Field(default=0, ge=0)


class BehaviourRecommendation(BaseModel):
    model_config = ConfigDict(frozen=True)

    recommendation_id: str = Field(default_factory=lambda: f"rec_{uuid.uuid4().hex[:12]}")
    behavior_key: str = Field(min_length=1)
    current_mode: str = Field(min_length=1)
    recommended_mode: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    confidence_basis: float = Field(default=0.5, ge=0.0, le=1.0)
    suggested_params: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class LearningPipelineResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    success: bool
    calibration_result: Optional[CalibrationResult] = None
    reward_signal: Optional[RewardSignal] = None
    strategy_record: Optional[StrategyLearningRecord] = None
    recommendations: List[BehaviourRecommendation] = Field(default_factory=list)
    error_message: Optional[str] = None
    processing_time_ms: float = Field(default=0.0, ge=0.0)
