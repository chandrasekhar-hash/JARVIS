import time
from typing import Dict, Any
from .metrics import wake_word_metrics, WakeWordMetrics


class HealthMonitor:
    """
    Health Monitoring subsystem tracking engine running state, microphone connectivity,
    frame counts, false positives, CPU/RAM usage, and diagnostic logs.
    """

    def __init__(self, metrics: Optional[WakeWordMetrics] = None):
        self.metrics = metrics or wake_word_metrics
        self.status = "STOPPED"
        self.mic_connected = False
        self.recovery_count = 0

    def set_status(self, new_status: str, mic_connected: bool = True):
        self.status = new_status
        self.mic_connected = mic_connected

    def record_recovery(self):
        self.recovery_count += 1

    def get_health_report(self) -> Dict[str, Any]:
        summary = self.metrics.get_summary()
        return {
            "status": self.status,
            "microphone_connected": self.mic_connected,
            "recovery_count": self.recovery_count,
            "metrics": summary,
            "health_state": "HEALTHY" if self.status == "RUNNING" and self.mic_connected else "DEGRADED"
        }


health_monitor = HealthMonitor()
