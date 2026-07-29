"""
Telemetry Metrics Collector for J.A.R.V.I.S. Phase V1.7.
Aggregates performance snapshots across profiler, memory, queue, retry, and health subsystems.
"""
from typing import Dict, Any, Optional
from .coordinator import PerformanceCoordinator


class PerformanceMetrics:
    """Aggregates system performance & reliability metrics."""

    def __init__(self, coordinator: Optional[PerformanceCoordinator] = None):
        self.coordinator = coordinator

    def get_summary(self) -> Dict[str, Any]:
        if not self.coordinator:
            return {}

        snapshot = self.coordinator.get_snapshot()
        perf_summary = self.coordinator.performance_manager.get_summary()
        rel_summary = self.coordinator.reliability_manager.get_summary()
        obs_snapshot = self.coordinator.registry.get_snapshot()

        return {
            "snapshot": snapshot.__dict__,
            "performance": perf_summary,
            "reliability": rel_summary,
            "observability": obs_snapshot,
        }
