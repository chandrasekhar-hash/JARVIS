"""
Performance Coordinator for J.A.R.V.I.S. Phase V1.7.
Directs Execution across PerformanceManager, ReliabilityManager, and MetricsRegistry.
"""
from typing import Optional, Dict, Any

from .config import PerformanceConfig, performance_config
from .registry import metrics_registry, MetricsRegistry
from .performance_manager import PerformanceManager
from .reliability_manager import ReliabilityManager
from .models import PerformanceSnapshot


class PerformanceCoordinator:
    """
    Global Performance & Reliability Coordinator.
    """

    def __init__(
        self,
        config: Optional[PerformanceConfig] = None,
        registry: Optional[MetricsRegistry] = None,
    ):
        self.config = config or performance_config
        self.registry = registry or metrics_registry

        self.performance_manager = PerformanceManager(config=self.config, registry=self.registry)
        self.reliability_manager = ReliabilityManager(config=self.config)

    async def start(self) -> None:
        await self.reliability_manager.start()

    async def stop(self) -> None:
        await self.reliability_manager.stop()

    def get_snapshot(self) -> PerformanceSnapshot:
        mem = self.reliability_manager.memory_monitor.get_statistics()
        speech_m = self.performance_manager.profiler.get_metrics("Speech")
        task_stats = self.performance_manager.task_scheduler.get_statistics()
        queue_stats = self.performance_manager.queue_manager.get_statistics()
        health = self.reliability_manager.health_scorer.get_overall_score()

        return PerformanceSnapshot(
            latency_p50=speech_m.p50_ms,
            latency_p90=speech_m.p90_ms,
            latency_p99=speech_m.p99_ms,
            rss_memory_mb=mem.rss_mb,
            cpu_percent=0.0,
            active_workers=task_stats.active_workers,
            queue_depth=queue_stats.current_size,
            health_score=health,
        )
