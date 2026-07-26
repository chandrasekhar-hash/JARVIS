import time
from typing import List, Dict, Optional, Any
from self_optimization.models import PerformanceSnapshot, SystemMetrics, PerformanceTrend
from brain.event_bus import event_bus, EventBus
from tools.telemetry import log_structured, backend_log


class PerformanceAnalyzer:
    """
    Analyzes system performance trends and computes aggregate SystemMetrics.
    SLA Target: Analysis < 100 ms.
    """

    def __init__(self, bus: Optional[EventBus] = None):
        self.event_bus = bus or event_bus

    def compute_system_metrics(self, snapshot: PerformanceSnapshot) -> SystemMetrics:
        start = time.perf_counter()
        try:
            lm = snapshot.learning_metrics or {}
            cm = snapshot.context_metrics or {}
            pm = snapshot.prediction_metrics or {}
            cnm = snapshot.continuity_metrics or {}

            # Calculate total end-to-end latency
            ctx_lat = float(cm.get("assembly_time_ms", 0.0))
            pred_lat = float(pm.get("prediction_latency_ms", 0.0))
            cont_lat = float(cnm.get("pipeline_time_ms", 0.0))
            total_latency = ctx_lat + pred_lat + cont_lat

            # Quality metrics
            avg_confidence = float(lm.get("average_confidence", 0.5))
            success_rate = 1.0 if float(lm.get("failed_learnings", 0)) == 0 else 0.85

            system_metrics = SystemMetrics(
                latency_ms=round(total_latency, 2),
                throughput=1.0,
                success_rate=round(success_rate, 2),
                prediction_accuracy=round(avg_confidence, 2),
                context_quality=0.90 if ctx_lat < 200.0 else 0.60,
                continuity_quality=0.95 if cont_lat < 100.0 else 0.70,
                provider_health_score=1.0,
                event_throughput=10.0,
                timestamp=time.time(),
            )

            elapsed_ms = (time.perf_counter() - start) * 1000.0
            if elapsed_ms > 100.0:
                log_structured(
                    backend_log,
                    "WARNING",
                    f"[PerformanceAnalyzer] Analysis SLA threshold exceeded: {elapsed_ms:.2f} ms",
                )

            log_structured(
                backend_log,
                "INFO",
                f"[PerformanceAnalyzer] Computed system metrics (Latency: {system_metrics.latency_ms} ms) in {elapsed_ms:.2f} ms",
            )
            return system_metrics

        except Exception as e:
            log_structured(backend_log, "ERROR", f"[PerformanceAnalyzer] Metric computation error: {str(e)}")
            return SystemMetrics(timestamp=time.time())

    def analyze_trends(self, snapshot: PerformanceSnapshot) -> List[PerformanceTrend]:
        trends: List[PerformanceTrend] = []
        try:
            sys_metrics = self.compute_system_metrics(snapshot)

            trends.append(
                PerformanceTrend(
                    metric_name="system_latency_ms",
                    direction="stable" if sys_metrics.latency_ms < 300.0 else "degrading",
                    percentage_change=0.0,
                    historical_average=250.0,
                    current_value=sys_metrics.latency_ms,
                )
            )

            trends.append(
                PerformanceTrend(
                    metric_name="prediction_accuracy",
                    direction="improving" if sys_metrics.prediction_accuracy > 0.70 else "degrading",
                    percentage_change=5.0,
                    historical_average=0.75,
                    current_value=sys_metrics.prediction_accuracy,
                )
            )

            self.event_bus.emit(
                "PerformanceAnalysed",
                snapshot_id=snapshot.snapshot_id,
                health_status="degrading" if sys_metrics.latency_ms > 500.0 else "healthy",
            )

            return trends

        except Exception as e:
            log_structured(backend_log, "ERROR", f"[PerformanceAnalyzer] Trend analysis error: {str(e)}")
            return trends
