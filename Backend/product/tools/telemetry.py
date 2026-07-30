"""
Product 1.5 Telemetry Collector and Execution Structured Logger.
"""
import os
import json
import time
import logging
from typing import Dict, Any, List, Optional
from .models import ExecutionMetrics, ToolExecutionResult, ExecutionContext

logger = logging.getLogger("JARVIS_ExecutionLogger")


class ExecutionTelemetryCollector:
    """
    In-memory metrics collector tracking throughput, success/failure rate,
    latencies, timeouts, retries, and usage statistics.
    """

    def __init__(self):
        self._metrics = ExecutionMetrics()
        self._durations: List[float] = []

    def record_execution(self, result: ToolExecutionResult) -> None:
        """Records telemetry data from a completed execution result."""
        self._metrics.total_executions += 1
        self._metrics.total_retries += max(0, result.attempts - 1)
        self._metrics.total_duration_ms += result.duration_ms
        self._durations.append(result.duration_ms)

        # Update per-tool usage
        t_id = result.tool_id
        self._metrics.tool_usage_counts[t_id] = self._metrics.tool_usage_counts.get(t_id, 0) + 1

        if result.success:
            self._metrics.successful_executions += 1
        else:
            self._metrics.failed_executions += 1
            if result.status.value == "TIMEOUT":
                self._metrics.total_timeouts += 1

        # Calculate latency percentiles
        if self._durations:
            sorted_dur = sorted(self._durations)
            n = len(sorted_dur)
            self._metrics.latency_p50_ms = sorted_dur[int(n * 0.50)]
            self._metrics.latency_p90_ms = sorted_dur[int(n * 0.90)] if n >= 10 else sorted_dur[-1]
            self._metrics.latency_p99_ms = sorted_dur[int(n * 0.99)] if n >= 100 else sorted_dur[-1]

    def get_metrics(self) -> ExecutionMetrics:
        """Returns snapshot of current execution telemetry metrics."""
        return self._metrics


class ExecutionLogger:
    """
    Writes structured JSON log entries for execution correlation and auditing.
    """

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(self.log_dir, "tool_execution.log")

    def log_execution(
        self,
        context: ExecutionContext,
        result: ToolExecutionResult,
        kwargs: Dict[str, Any],
    ) -> None:
        """Writes structured JSON execution log entry."""
        log_entry = {
            "timestamp": time.time(),
            "correlation_id": context.correlation_id,
            "tool_id": context.tool_id,
            "user_id": context.user_id,
            "status": result.status.value,
            "success": result.success,
            "duration_ms": result.duration_ms,
            "attempts": result.attempts,
            "parameters_summary": {k: str(v)[:64] for k, v in kwargs.items() if k != "password"},
            "error_message": result.error_message,
        }

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.warning(f"[ExecutionLogger] Failed to write log file: {e}")

        logger.info(
            f"[ExecutionLogger] [{result.status.value}] Tool '{context.tool_id}' "
            f"completed in {result.duration_ms:.1f}ms (Attempts: {result.attempts})."
        )


# Global singleton instances
telemetry_collector_instance = ExecutionTelemetryCollector()
execution_logger_instance = ExecutionLogger()
