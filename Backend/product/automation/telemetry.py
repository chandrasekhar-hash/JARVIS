"""
JARVIS Product 1.7 - Automation Telemetry.
Collects telemetry metrics for workflows executed, success/failure counts, queue depth, and latencies.
"""

from typing import Dict, Any


class AutomationTelemetry:
    def __init__(self):
        self.total_executions = 0
        self.successful_executions = 0
        self.failed_executions = 0
        self.total_duration_ms = 0.0

    def record_execution(self, success: bool, duration_ms: float):
        self.total_executions += 1
        if success:
            self.successful_executions += 1
        else:
            self.failed_executions += 1
        self.total_duration_ms += duration_ms

    def get_metrics(self) -> Dict[str, Any]:
        success_rate = (self.successful_executions / max(1, self.total_executions)) * 100.0
        avg_latency = self.total_duration_ms / max(1, self.total_executions)
        return {
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "success_rate_pct": round(success_rate, 2),
            "average_duration_ms": round(avg_latency, 2),
        }


automation_telemetry = AutomationTelemetry()
