import time
import asyncio
from typing import Dict, List, Optional, Any
from self_optimization.models import (
    OptimisationResult,
    OptimisationMetrics,
    SystemMetrics,
    OptimisationReport,
)
from self_optimization.interfaces import (
    IMetricsCollector,
    IPerformanceAnalyzer,
    IBottleneckDetector,
    IRecommendationEngine,
)
from self_optimization.metrics_collector import MetricsCollector
from self_optimization.performance_analyzer import PerformanceAnalyzer
from self_optimization.bottleneck_detector import BottleneckDetector
from self_optimization.recommendation_engine import RecommendationEngine
from brain.event_bus import event_bus, EventBus
from tools.telemetry import log_structured, backend_log


class SelfOptimizationEngine:
    """
    Main Self-Optimisation Engine for Milestone 7.6.
    Continuously evaluates system performance across Phase 7 modules and produces optimization reports and recommendations.
    ROLE IS ANALYSIS AND RECOMMENDATION ONLY.
    Does NOT modify runtime behavior, rewrite configurations, alter user preferences, retrain models, or execute actions.
    """

    def __init__(
        self,
        collector: Optional[IMetricsCollector] = None,
        analyzer: Optional[IPerformanceAnalyzer] = None,
        detector: Optional[IBottleneckDetector] = None,
        recommender: Optional[IRecommendationEngine] = None,
        bus: Optional[EventBus] = None,
    ):
        self.event_bus = bus or event_bus
        self.collector = collector or MetricsCollector(bus=self.event_bus)
        self.analyzer = analyzer or PerformanceAnalyzer(bus=self.event_bus)
        self.detector = detector or BottleneckDetector(bus=self.event_bus)
        self.recommender = recommender or RecommendationEngine(bus=self.event_bus)

    async def analyze_and_recommend(
        self,
        learning_metrics: Optional[Dict[str, Any]] = None,
        context_metrics: Optional[Dict[str, Any]] = None,
        prediction_metrics: Optional[Dict[str, Any]] = None,
        continuity_metrics: Optional[Dict[str, Any]] = None,
    ) -> OptimisationResult:
        start_time = time.perf_counter()
        try:
            # Step 1 & 2: Collect & Aggregate Metrics
            snapshot = self.collector.collect_metrics(
                learning_metrics=learning_metrics,
                context_metrics=context_metrics,
                prediction_metrics=prediction_metrics,
                continuity_metrics=continuity_metrics,
            )

            # Step 3: Compute System Metrics & Analyze Trends (< 100 ms SLA)
            analysis_start = time.perf_counter()
            system_metrics = self.analyzer.compute_system_metrics(snapshot)
            trends = self.analyzer.analyze_trends(snapshot)
            analysis_time_ms = (time.perf_counter() - analysis_start) * 1000.0

            # Step 4: Detect Bottlenecks
            bottlenecks = self.detector.detect_bottlenecks(snapshot, trends)

            # Step 5 & 6: Generate & Prioritise Recommendations (< 30 ms SLA)
            rec_start = time.perf_counter()
            recommendations = self.recommender.generate_recommendations(bottlenecks, trends)
            rec_time_ms = (time.perf_counter() - rec_start) * 1000.0

            # Step 7: Generate Report
            report = self.recommender.build_report(trends, bottlenecks, recommendations)

            # Step 8: Events published automatically via sub-components

            metrics = OptimisationMetrics(
                analysis_latency_ms=analysis_time_ms,
                recommendation_latency_ms=rec_time_ms,
                total_bottlenecks_found=len(bottlenecks),
                total_recommendations_generated=len(recommendations),
                timestamp=time.time(),
            )

            pipeline_ms = (time.perf_counter() - start_time) * 1000.0
            log_structured(
                backend_log,
                "INFO",
                f"[SelfOptimizationEngine] Pipeline analysis complete in {pipeline_ms:.2f} ms ({len(recommendations)} recommendations)",
            )

            # Step 9: Return OptimisationResult
            return OptimisationResult(
                success=True,
                system_metrics=system_metrics,
                report=report,
                metrics=metrics,
            )

        except Exception as e:
            log_structured(backend_log, "ERROR", f"[SelfOptimizationEngine] Analysis pipeline error: {str(e)}")
            return OptimisationResult(
                success=False,
                error_message=f"Self-optimisation exception: {str(e)}",
            )


# Default global instance
self_optimization_engine = SelfOptimizationEngine()
