from typing import Protocol, List, Optional, Dict, Any
from self_optimization.models import (
    PerformanceSnapshot,
    SystemMetrics,
    PerformanceTrend,
    Bottleneck,
    OptimisationRecommendation,
    OptimisationReport,
    OptimisationResult,
)


class IMetricsCollector(Protocol):
    def collect_metrics(
        self,
        learning_metrics: Optional[Dict[str, Any]] = None,
        context_metrics: Optional[Dict[str, Any]] = None,
        prediction_metrics: Optional[Dict[str, Any]] = None,
        continuity_metrics: Optional[Dict[str, Any]] = None,
    ) -> PerformanceSnapshot:
        ...


class IPerformanceAnalyzer(Protocol):
    def analyze_trends(
        self, snapshot: PerformanceSnapshot
    ) -> List[PerformanceTrend]:
        ...

    def compute_system_metrics(
        self, snapshot: PerformanceSnapshot
    ) -> SystemMetrics:
        ...


class IBottleneckDetector(Protocol):
    def detect_bottlenecks(
        self, snapshot: PerformanceSnapshot, trends: List[PerformanceTrend]
    ) -> List[Bottleneck]:
        ...


class IRecommendationEngine(Protocol):
    def generate_recommendations(
        self, bottlenecks: List[Bottleneck], trends: List[PerformanceTrend]
    ) -> List[OptimisationRecommendation]:
        ...

    def build_report(
        self,
        trends: List[PerformanceTrend],
        bottlenecks: List[Bottleneck],
        recommendations: List[OptimisationRecommendation],
    ) -> OptimisationReport:
        ...


class ISelfOptimizationEngine(Protocol):
    async def analyze_and_recommend(
        self,
        learning_metrics: Optional[Dict[str, Any]] = None,
        context_metrics: Optional[Dict[str, Any]] = None,
        prediction_metrics: Optional[Dict[str, Any]] = None,
        continuity_metrics: Optional[Dict[str, Any]] = None,
    ) -> OptimisationResult:
        ...
