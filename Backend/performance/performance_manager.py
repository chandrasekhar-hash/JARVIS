"""
Performance Manager for J.A.R.V.I.S. Phase V1.7.
Coordinating Profiler, TaskScheduler, ResourcePools, QueueManager, LRUCache, PerformanceBudget, AdaptiveTuner.
"""
from typing import Optional, Dict, Any

from .config import PerformanceConfig, performance_config
from .registry import metrics_registry, MetricsRegistry
from .budget import PerformanceBudget
from .profiler import PerformanceProfiler
from .task_scheduler import TaskScheduler
from .resource_pool import ResourcePool
from .queue_manager import QueueManager
from .cache import LRUCache
from .tuner import AdaptiveTuner


class PerformanceManager:
    """
    Subsystem manager dedicated to execution speed, latency profiling, resource pooling, and adaptive tuning.
    """

    def __init__(
        self,
        config: Optional[PerformanceConfig] = None,
        registry: Optional[MetricsRegistry] = None,
    ):
        self.config = config or performance_config
        self.registry = registry or metrics_registry

        self.budget = PerformanceBudget(config=self.config)
        self.profiler = PerformanceProfiler(registry=self.registry, budget=self.budget)
        self.task_scheduler = TaskScheduler(
            initial_workers=self.config.initial_worker_count,
            max_workers=self.config.max_worker_count,
        )
        self.queue_manager = QueueManager(default_capacity=self.config.max_queue_size)
        self.cache = LRUCache(
            capacity=self.config.cache_capacity,
            default_ttl_sec=self.config.cache_ttl_sec,
        )
        self.adaptive_tuner = AdaptiveTuner(
            scheduler=self.task_scheduler,
            profiler=self.profiler,
            config=self.config,
        )

        # Pre-allocated default byte buffer pool
        self.buffer_pool = ResourcePool(
            factory_fn=lambda: bytearray(3200),
            pool_name="audio_pcm_buffers",
            max_size=self.config.max_pool_size,
        )

    def record_operation_latency(self, operation: str, latency_ms: float) -> None:
        self.profiler.record_latency(operation, latency_ms)

    def tune(self) -> None:
        self.adaptive_tuner.evaluate_and_tune()

    def get_summary(self) -> Dict[str, Any]:
        return {
            "profiler_operations": list(self.profiler._samples.keys()),
            "budgets": self.budget.get_summary(),
            "scheduler": self.task_scheduler.get_statistics().__dict__,
            "queue": self.queue_manager.get_statistics().__dict__,
            "cache": self.cache.get_statistics(),
            "buffer_pool": self.buffer_pool.get_statistics().__dict__,
        }
