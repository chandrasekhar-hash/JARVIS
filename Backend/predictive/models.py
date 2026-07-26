import time
import uuid
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


class PredictionConfidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    overall_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    context_quality_score: float = Field(default=0.5, ge=0.0, le=1.0)
    user_habit_alignment: float = Field(default=0.5, ge=0.0, le=1.0)
    signal_agreement_score: float = Field(default=0.5, ge=0.0, le=1.0)
    freshness_score: float = Field(default=1.0, ge=0.0, le=1.0)


class PredictionExplanation(BaseModel):
    model_config = ConfigDict(frozen=True)

    prediction_id: str = Field(default_factory=lambda: f"pred_exp_{uuid.uuid4().hex[:12]}")
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_evidence: List[str] = Field(default_factory=list)
    trigger_signals: List[str] = Field(default_factory=list)
    reasoning_summary: str = Field(min_length=1)
    source_providers: List[str] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)


class GoalPrediction(BaseModel):
    model_config = ConfigDict(frozen=True)

    prediction_id: str = Field(default_factory=lambda: f"gpred_{uuid.uuid4().hex[:12]}")
    predicted_goal: str = Field(min_length=1)
    intent_category: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: PredictionExplanation
    suggested_parameters: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class IntentPrediction(BaseModel):
    model_config = ConfigDict(frozen=True)

    intent_category: str = Field(min_length=1)
    probability: float = Field(ge=0.0, le=1.0)
    matched_signals: List[str] = Field(default_factory=list)


class WorkflowPrediction(BaseModel):
    model_config = ConfigDict(frozen=True)

    workflow_id: str = Field(default_factory=lambda: f"wfpred_{uuid.uuid4().hex[:12]}")
    predicted_tool_sequence: List[str] = Field(default_factory=list)
    predicted_actions: List[str] = Field(default_factory=list)
    completion_probability: float = Field(default=0.5, ge=0.0, le=1.0)


class PredictionCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidate_id: str = Field(default_factory=lambda: f"cand_{uuid.uuid4().hex[:12]}")
    goal_description: str = Field(min_length=1)
    intent_category: str = Field(min_length=1)
    raw_score: float = Field(default=0.5, ge=0.0, le=1.0)
    signals: List[str] = Field(default_factory=list)


class Suggestion(BaseModel):
    model_config = ConfigDict(frozen=True)

    suggestion_id: str = Field(default_factory=lambda: f"sug_{uuid.uuid4().hex[:12]}")
    title: str = Field(min_length=1)
    recommended_action: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str = Field(min_length=1)
    timestamp: float = Field(default_factory=time.time)


class PredictionMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    total_predictions_made: int = Field(default=0, ge=0)
    high_confidence_predictions: int = Field(default=0, ge=0)
    suggestions_generated: int = Field(default=0, ge=0)
    prediction_latency_ms: float = Field(default=0.0, ge=0.0)
    timestamp: float = Field(default_factory=time.time)


class PredictionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    success: bool
    context_id: str = Field(default="")
    goal_predictions: List[GoalPrediction] = Field(default_factory=list)
    workflow_predictions: List[WorkflowPrediction] = Field(default_factory=list)
    suggestions: List[Suggestion] = Field(default_factory=list)
    metrics: PredictionMetrics = Field(default_factory=PredictionMetrics)
    error_message: Optional[str] = None
