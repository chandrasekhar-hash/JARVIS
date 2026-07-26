import time
import uuid
from enum import IntEnum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class RecommendationPriority(IntEnum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


class SystemMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    metrics_id: str = Field(default_factory=lambda: f"sysm_{uuid.uuid4().hex[:12]}")
    latency_ms: float = Field(default=0.0, ge=0.0)
    throughput: float = Field(default=0.0, ge=0.0)
    success_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    prediction_accuracy: float = Field(default=0.8, ge=0.0, le=1.0)
    context_quality: float = Field(default=0.8, ge=0.0, le=1.0)
    continuity_quality: float = Field(default=0.8, ge=0.0, le=1.0)
    provider_health_score: float = Field(default=1.0, ge=0.0, le=1.0)
    event_throughput: float = Field(default=0.0, ge=0.0)
    timestamp: float = Field(default_factory=time.time)


class PerformanceSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: str = Field(default_factory=lambda: f"snap_{uuid.uuid4().hex[:12]}")
    learning_metrics: Optional[Dict[str, Any]] = None
    context_metrics: Optional[Dict[str, Any]] = None
    prediction_metrics: Optional[Dict[str, Any]] = None
    continuity_metrics: Optional[Dict[str, Any]] = None
    timestamp: float = Field(default_factory=time.time)


class PerformanceTrend(BaseModel):
    model_config = ConfigDict(frozen=True)

    metric_name: str = Field(min_length=1)
    direction: str = Field(default="stable")  # "improving", "stable", "degrading"
    percentage_change: float = Field(default=0.0)
    historical_average: float = Field(default=0.0)
    current_value: float = Field(default=0.0)


class Bottleneck(BaseModel):
    model_config = ConfigDict(frozen=True)

    bottleneck_id: str = Field(default_factory=lambda: f"btnk_{uuid.uuid4().hex[:12]}")
    subsystem: str = Field(min_length=1)
    bottleneck_type: str = Field(min_length=1)  # "high_latency", "slow_provider", "low_confidence", etc.
    severity: str = Field(default="medium")  # "low", "medium", "high", "critical"
    description: str = Field(min_length=1)
    impact_summary: str = Field(min_length=1)
    timestamp: float = Field(default_factory=time.time)


class OptimisationRecommendation(BaseModel):
    model_config = ConfigDict(frozen=True)

    recommendation_id: str = Field(default_factory=lambda: f"optrec_{uuid.uuid4().hex[:12]}")
    target_subsystem: str = Field(min_length=1)
    parameter_key: str = Field(min_length=1)
    current_value: Any
    proposed_value: Any
    priority: RecommendationPriority = RecommendationPriority.MEDIUM
    rationale: str = Field(min_length=1)
    estimated_improvement: str = Field(min_length=1)
    timestamp: float = Field(default_factory=time.time)


class OptimisationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_id: str = Field(default_factory=lambda: f"optrpt_{uuid.uuid4().hex[:12]}")
    executive_summary: str = Field(min_length=1)
    technical_report: str = Field(min_length=1)
    trends: List[PerformanceTrend] = Field(default_factory=list)
    bottlenecks: List[Bottleneck] = Field(default_factory=list)
    recommendations: List[OptimisationRecommendation] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)


class OptimisationMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    analysis_latency_ms: float = Field(default=0.0, ge=0.0)
    recommendation_latency_ms: float = Field(default=0.0, ge=0.0)
    total_bottlenecks_found: int = Field(default=0, ge=0)
    total_recommendations_generated: int = Field(default=0, ge=0)
    timestamp: float = Field(default_factory=time.time)


class OptimisationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    success: bool
    system_metrics: Optional[SystemMetrics] = None
    report: Optional[OptimisationReport] = None
    metrics: OptimisationMetrics = Field(default_factory=OptimisationMetrics)
    error_message: Optional[str] = None
