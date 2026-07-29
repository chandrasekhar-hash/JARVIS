"""
Performance Profiler for J.A.R.V.I.S. Phase V1.7.
Collects execution latencies, calculates rolling p50/p90/p99 percentiles,
and integrates with MetricsRegistry & PerformanceBudget.
"""
import time
import math
import logging
from typing import Dict, List, Optional

from .interfaces import IPerformanceProfiler
from .models import LatencyMetrics
from .registry import metrics_registry, MetricsRegistry
from .budget import PerformanceBudget

logger = logging.getLogger("JARVIS_PerformanceProfiler")


class PerformanceProfiler(IPerformanceProfiler):
    """
    Real-time execution latency profiler.
    """

    def __init__(self, registry: Optional[MetricsRegistry] = None, budget: Optional[PerformanceBudget] = None):
        self.registry = registry or metrics_registry
        self.budget = budget or PerformanceBudget()
        self._samples: Dict[str, List[float]] = {}
        self._history_capacity: int = 1000

    def record_latency(self, operation: str, latency_ms: float) -> None:
        """Records latency observation in ms for operation."""
        if operation not in self._samples:
            self._samples[operation] = []

        samples = self._samples[operation]
        samples.append(latency_ms)
        if len(samples) > self._history_capacity:
            samples.pop(0)

        # Update metrics registry histogram & timer
        timer = self.registry.timer(operation)
        timer.record(latency_ms)

        # Check performance SLA budget
        if operation in self.budget.budgets:
            status = self.budget.check_budget(operation, latency_ms)
            if status.breached:
                logger.warning(
                    f"[PerformanceProfiler] SLA Budget Breach for '{operation}': "
                    f"Actual {latency_ms:.2f}ms > Budget {status.budget_ms:.2f}ms"
                )

    def get_metrics(self, operation: str = "default") -> LatencyMetrics:
        samples = self._samples.get(operation, [])
        if not samples:
            return LatencyMetrics(operation=operation)

        sorted_samples = sorted(samples)
        count = len(sorted_samples)
        min_ms = sorted_samples[0]
        max_ms = sorted_samples[-1]
        avg_ms = sum(sorted_samples) / count

        def calc_p(p: float) -> float:
            idx = int(math.ceil((p / 100.0) * count)) - 1
            idx = max(0, min(idx, count - 1))
            return sorted_samples[idx]

        return LatencyMetrics(
            operation=operation,
            sample_count=count,
            min_ms=round(min_ms, 2),
            max_ms=round(max_ms, 2),
            avg_ms=round(avg_ms, 2),
            p50_ms=round(calc_p(50), 2),
            p90_ms=round(calc_p(90), 2),
            p99_ms=round(calc_p(99), 2),
        )

    def get_all_metrics(self) -> Dict[str, LatencyMetrics]:
        return {op: self.get_metrics(op) for op in self._samples.keys()}
