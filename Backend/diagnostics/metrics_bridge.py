"""
Metrics Bridge for J.A.R.V.I.S. Phase V1.8.
Connects Diagnostics to V1.7 Performance MetricsRegistry primitives (Counters, Gauges, Histograms, Timers).
"""
from typing import Dict, Any, Optional


class MetricsBridge:
    """
    Adapter reading metrics primitives from Phase V1.7 MetricsRegistry.
    """

    def __init__(self):
        try:
            from performance import metrics_registry
            self.registry = metrics_registry
        except ImportError:
            self.registry = None

    def read_metrics_snapshot(self) -> Dict[str, Any]:
        if self.registry:
            return self.registry.get_snapshot()
        return {"counters": {}, "gauges": {}, "histograms": {}}
