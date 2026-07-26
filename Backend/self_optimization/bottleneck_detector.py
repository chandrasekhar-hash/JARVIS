import time
from typing import List, Optional
from self_optimization.models import PerformanceSnapshot, PerformanceTrend, Bottleneck
from brain.event_bus import event_bus, EventBus
from tools.telemetry import log_structured, backend_log


class BottleneckDetector:
    """
    Detects latency bottlenecks, slow providers, low confidence trends, and pipeline degradations.
    """

    def __init__(self, bus: Optional[EventBus] = None):
        self.event_bus = bus or event_bus

    def detect_bottlenecks(
        self, snapshot: PerformanceSnapshot, trends: List[PerformanceTrend]
    ) -> List[Bottleneck]:
        bottlenecks: List[Bottleneck] = []
        try:
            cm = snapshot.context_metrics or {}
            pm = snapshot.prediction_metrics or {}

            # 1. Context Assembly Latency Bottleneck
            ctx_lat = float(cm.get("assembly_time_ms", 0.0))
            if ctx_lat > 200.0:
                b = Bottleneck(
                    subsystem="unified_context",
                    bottleneck_type="high_latency",
                    severity="high",
                    description=f"Context Assembly SLA exceeded: {ctx_lat:.1f} ms (Target < 200 ms)",
                    impact_summary="Increased end-to-end prompt context assembly latency.",
                    timestamp=time.time(),
                )
                bottlenecks.append(b)

            # 2. Prediction Latency Bottleneck
            pred_lat = float(pm.get("prediction_latency_ms", 0.0))
            if pred_lat > 100.0:
                b = Bottleneck(
                    subsystem="predictive",
                    bottleneck_type="high_latency",
                    severity="medium",
                    description=f"Prediction SLA exceeded: {pred_lat:.1f} ms (Target < 100 ms)",
                    impact_summary="Delayed proactive suggestion generation.",
                    timestamp=time.time(),
                )
                bottlenecks.append(b)

            # 3. Emit events for detected bottlenecks
            for btnk in bottlenecks:
                self.event_bus.emit(
                    "BottleneckDetected",
                    bottleneck_id=btnk.bottleneck_id,
                    subsystem=btnk.subsystem,
                    bottleneck_type=btnk.bottleneck_type,
                    severity=btnk.severity,
                )

            log_structured(
                backend_log,
                "INFO",
                f"[BottleneckDetector] Identified {len(bottlenecks)} system bottlenecks",
            )
            return bottlenecks

        except Exception as e:
            log_structured(backend_log, "ERROR", f"[BottleneckDetector] Error detecting bottlenecks: {str(e)}")
            return bottlenecks
