"""
Adaptive Optimization Tuner for J.A.R.V.I.S. Phase V1.7.
Dynamically scales worker pools and queue limits based on real-time latency feedback loops.
"""
import logging
from typing import Optional
from .config import PerformanceConfig, performance_config
from .task_scheduler import TaskScheduler
from .profiler import PerformanceProfiler

logger = logging.getLogger("JARVIS_AdaptiveTuner")


class AdaptiveTuner:
    """
    Adaptive self-tuning optimization controller.
    """

    def __init__(
        self,
        scheduler: TaskScheduler,
        profiler: PerformanceProfiler,
        config: PerformanceConfig = performance_config,
    ):
        self.scheduler = scheduler
        self.profiler = profiler
        self.config = config

    def evaluate_and_tune(self) -> None:
        """Evaluates recent system latency and adapts worker pool scaling."""
        if not self.config.adaptive_tuning_enabled:
            return

        speech_metrics = self.profiler.get_metrics("Speech")
        avg_latency = speech_metrics.avg_ms or speech_metrics.p50_ms

        curr_workers = self.scheduler.get_statistics().active_workers

        # High latency condition: Expand worker pool
        if avg_latency > self.config.high_latency_threshold_ms:
            new_workers = min(curr_workers + 2, self.config.max_worker_count)
            if new_workers != curr_workers:
                self.scheduler.adjust_worker_count(new_workers)
                logger.info(
                    f"[AdaptiveTuner] High latency detected ({avg_latency:.2f}ms > {self.config.high_latency_threshold_ms:.2f}ms). "
                    f"Scaled worker pool: {curr_workers} -> {new_workers}."
                )

        # Low latency condition: Contract worker pool
        elif avg_latency > 0 and avg_latency < self.config.low_latency_threshold_ms:
            new_workers = max(curr_workers - 1, self.config.initial_worker_count)
            if new_workers != curr_workers:
                self.scheduler.adjust_worker_count(new_workers)
                logger.info(
                    f"[AdaptiveTuner] Low latency detected ({avg_latency:.2f}ms). "
                    f"Scaled back worker pool: {curr_workers} -> {new_workers}."
                )
