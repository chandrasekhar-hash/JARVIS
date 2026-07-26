import time
from typing import Dict, Optional, Any
from self_optimization.models import PerformanceSnapshot
from brain.event_bus import event_bus, EventBus
from tools.telemetry import log_structured, backend_log


class MetricsCollector:
    """
    Collects and aggregates subsystem performance metrics snapshots without querying storage drivers directly.
    """

    def __init__(self, bus: Optional[EventBus] = None):
        self.event_bus = bus or event_bus

    def collect_metrics(
        self,
        learning_metrics: Optional[Dict[str, Any]] = None,
        context_metrics: Optional[Dict[str, Any]] = None,
        prediction_metrics: Optional[Dict[str, Any]] = None,
        continuity_metrics: Optional[Dict[str, Any]] = None,
    ) -> PerformanceSnapshot:
        snapshot = PerformanceSnapshot(
            learning_metrics=learning_metrics or {},
            context_metrics=context_metrics or {},
            prediction_metrics=prediction_metrics or {},
            continuity_metrics=continuity_metrics or {},
            timestamp=time.time(),
        )

        self.event_bus.emit(
            "MetricsCollected",
            snapshot_id=snapshot.snapshot_id,
            timestamp=snapshot.timestamp,
        )

        log_structured(
            backend_log,
            "INFO",
            f"[MetricsCollector] Collected performance snapshot '{snapshot.snapshot_id}'",
        )
        return snapshot
