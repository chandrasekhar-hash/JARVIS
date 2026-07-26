import os
import sys
import time
import asyncio
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from self_optimization.models import (
    SystemMetrics,
    PerformanceSnapshot,
    PerformanceTrend,
    Bottleneck,
    OptimisationRecommendation,
    RecommendationPriority,
    OptimisationReport,
    OptimisationResult,
)
from self_optimization.metrics_collector import MetricsCollector
from self_optimization.performance_analyzer import PerformanceAnalyzer
from self_optimization.bottleneck_detector import BottleneckDetector
from self_optimization.recommendation_engine import RecommendationEngine
from self_optimization.engine import SelfOptimizationEngine
from brain.event_bus import EventBus


class TestSelfOptimizationPhase7(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.learning_metrics = {"average_confidence": 0.85, "failed_learnings": 0}
        self.context_metrics = {"assembly_time_ms": 250.0}  # SLA breach simulation > 200ms
        self.prediction_metrics = {"prediction_latency_ms": 120.0}  # SLA breach simulation > 100ms
        self.continuity_metrics = {"pipeline_time_ms": 15.0}

    async def test_metrics_collection(self):
        collector = MetricsCollector()
        snapshot = collector.collect_metrics(
            learning_metrics=self.learning_metrics,
            context_metrics=self.context_metrics,
        )
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.learning_metrics.get("average_confidence"), 0.85)

    async def test_performance_analysis_and_sla(self):
        collector = MetricsCollector()
        analyzer = PerformanceAnalyzer()

        snapshot = collector.collect_metrics(
            learning_metrics=self.learning_metrics,
            context_metrics=self.context_metrics,
            prediction_metrics=self.prediction_metrics,
            continuity_metrics=self.continuity_metrics,
        )

        start = time.perf_counter()
        sys_metrics = analyzer.compute_system_metrics(snapshot)
        trends = analyzer.analyze_trends(snapshot)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        # Analysis SLA < 100 ms
        self.assertLess(elapsed_ms, 100.0)
        self.assertGreater(sys_metrics.latency_ms, 0.0)
        self.assertGreater(len(trends), 0)

    async def test_bottleneck_detection(self):
        collector = MetricsCollector()
        analyzer = PerformanceAnalyzer()
        detector = BottleneckDetector()

        snapshot = collector.collect_metrics(
            context_metrics=self.context_metrics,
            prediction_metrics=self.prediction_metrics,
        )
        trends = analyzer.analyze_trends(snapshot)

        bottlenecks = detector.detect_bottlenecks(snapshot, trends)
        self.assertGreater(len(bottlenecks), 0)
        subsystems = [b.subsystem for b in bottlenecks]
        self.assertIn("unified_context", subsystems)

    async def test_recommendation_engine_and_sla(self):
        recommender = RecommendationEngine()
        bottlenecks = [
            Bottleneck(
                subsystem="unified_context",
                bottleneck_type="high_latency",
                severity="high",
                description="Context Assembly latency high",
                impact_summary="Slow prompt assembly",
            )
        ]

        start = time.perf_counter()
        recs = recommender.generate_recommendations(bottlenecks, [])
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        # Recommendation Generation SLA < 30 ms
        self.assertLess(elapsed_ms, 30.0)
        self.assertGreater(len(recs), 0)
        self.assertEqual(recs[0].target_subsystem, "unified_context")
        self.assertEqual(recs[0].parameter_key, "max_unified_context_tokens")

        report = recommender.build_report([], bottlenecks, recs)
        self.assertIsNotNone(report)
        self.assertIn("System performance audit completed", report.executive_summary)

    async def test_self_optimization_engine_full_pipeline(self):
        engine = SelfOptimizationEngine()

        start = time.perf_counter()
        result = await engine.analyze_and_recommend(
            learning_metrics=self.learning_metrics,
            context_metrics=self.context_metrics,
            prediction_metrics=self.prediction_metrics,
            continuity_metrics=self.continuity_metrics,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        self.assertTrue(result.success)
        self.assertIsNotNone(result.system_metrics)
        self.assertIsNotNone(result.report)
        self.assertGreater(len(result.report.recommendations), 0)

    async def test_event_publishing(self):
        custom_bus = EventBus()
        events_emitted = []

        def listener(evt):
            events_emitted.append(evt.name)

        custom_bus.subscribe("MetricsCollected", listener)
        custom_bus.subscribe("PerformanceAnalysed", listener)
        custom_bus.subscribe("BottleneckDetected", listener)
        custom_bus.subscribe("RecommendationGenerated", listener)
        custom_bus.subscribe("OptimisationReportGenerated", listener)

        engine = SelfOptimizationEngine(bus=custom_bus)
        await engine.analyze_and_recommend(
            context_metrics=self.context_metrics,
            prediction_metrics=self.prediction_metrics,
        )
        await asyncio.sleep(0.05)

        self.assertIn("MetricsCollected", events_emitted)
        self.assertIn("PerformanceAnalysed", events_emitted)
        self.assertIn("BottleneckDetected", events_emitted)
        self.assertIn("RecommendationGenerated", events_emitted)
        self.assertIn("OptimisationReportGenerated", events_emitted)


if __name__ == "__main__":
    unittest.main()
