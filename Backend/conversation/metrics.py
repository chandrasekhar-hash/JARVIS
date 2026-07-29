"""
Metrics collection and telemetry tracker for J.A.R.V.I.S. Phase V1.3 Conversation Engine.
"""
from typing import Dict, Any, List


class ConversationMetrics:
    """Tracks latency, turn metrics, error rates, and context size telemetry."""

    def __init__(self, history_size: int = 100):
        self.history_size = history_size
        self._turn_latencies_ms: List[float] = []
        self._response_latencies_ms: List[float] = []
        self._context_sizes: List[int] = []

        self.total_sessions: int = 0
        self.total_turns: int = 0
        self.total_errors: int = 0
        self.total_cancellations: int = 0

    def record_turn_latency(self, latency_ms: float) -> None:
        """Records total turn processing pipeline latency."""
        self._turn_latencies_ms.append(latency_ms)
        if len(self._turn_latencies_ms) > self.history_size:
            self._turn_latencies_ms.pop(0)

    def record_response_latency(self, latency_ms: float) -> None:
        """Records response provider generation latency."""
        self._response_latencies_ms.append(latency_ms)
        if len(self._response_latencies_ms) > self.history_size:
            self._response_latencies_ms.pop(0)

    def record_context_size(self, size: int) -> None:
        """Records working context size in turns."""
        self._context_sizes.append(size)
        if len(self._context_sizes) > self.history_size:
            self._context_sizes.pop(0)

    def get_summary(self) -> Dict[str, Any]:
        """Returns snapshot summary of conversation telemetry."""
        avg_turn_latency = (
            sum(self._turn_latencies_ms) / len(self._turn_latencies_ms)
            if self._turn_latencies_ms
            else 0.0
        )
        avg_response_latency = (
            sum(self._response_latencies_ms) / len(self._response_latencies_ms)
            if self._response_latencies_ms
            else 0.0
        )
        avg_context_size = (
            sum(self._context_sizes) / len(self._context_sizes)
            if self._context_sizes
            else 0
        )

        return {
            "total_sessions": self.total_sessions,
            "total_turns": self.total_turns,
            "total_errors": self.total_errors,
            "total_cancellations": self.total_cancellations,
            "avg_turn_latency_ms": round(avg_turn_latency, 2),
            "avg_response_latency_ms": round(avg_response_latency, 2),
            "avg_context_size": round(avg_context_size, 1),
        }

    def reset(self) -> None:
        """Resets conversation metric counters."""
        self._turn_latencies_ms.clear()
        self._response_latencies_ms.clear()
        self._context_sizes.clear()
        self.total_sessions = 0
        self.total_turns = 0
        self.total_errors = 0
        self.total_cancellations = 0


# Global singleton metrics instance
conversation_metrics = ConversationMetrics()
