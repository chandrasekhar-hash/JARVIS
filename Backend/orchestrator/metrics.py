"""
Metrics collection and telemetry tracker for J.A.R.V.I.S. Phase V1.6 Voice Orchestrator.
"""
from typing import Dict, Any, List


class OrchestratorMetrics:
    """Tracks session durations, turn counts, latencies, interrupts, cancellations, and timeouts."""

    def __init__(self, history_size: int = 100):
        self.history_size = history_size
        self._session_durations_sec: List[float] = []
        self._turns_per_session: List[int] = []
        self._recognition_latencies_ms: List[float] = []
        self._thinking_latencies_ms: List[float] = []
        self._speaking_latencies_ms: List[float] = []

        self.total_sessions: int = 0
        self.total_barge_ins: int = 0
        self.total_cancellations: int = 0
        self.total_recoveries: int = 0
        self.total_timeouts: int = 0
        self.total_errors: int = 0

    def record_session_duration(self, duration_sec: float) -> None:
        self._session_durations_sec.append(duration_sec)
        if len(self._session_durations_sec) > self.history_size:
            self._session_durations_sec.pop(0)

    def record_turns_count(self, turn_count: int) -> None:
        self._turns_per_session.append(turn_count)
        if len(self._turns_per_session) > self.history_size:
            self._turns_per_session.pop(0)

    def record_recognition_latency(self, latency_ms: float) -> None:
        self._recognition_latencies_ms.append(latency_ms)
        if len(self._recognition_latencies_ms) > self.history_size:
            self._recognition_latencies_ms.pop(0)

    def record_thinking_latency(self, latency_ms: float) -> None:
        self._thinking_latencies_ms.append(latency_ms)
        if len(self._thinking_latencies_ms) > self.history_size:
            self._thinking_latencies_ms.pop(0)

    def record_speaking_latency(self, latency_ms: float) -> None:
        self._speaking_latencies_ms.append(latency_ms)
        if len(self._speaking_latencies_ms) > self.history_size:
            self._speaking_latencies_ms.pop(0)

    def get_summary(self) -> Dict[str, Any]:
        avg_duration = (
            sum(self._session_durations_sec) / len(self._session_durations_sec)
            if self._session_durations_sec
            else 0.0
        )
        avg_turns = (
            sum(self._turns_per_session) / len(self._turns_per_session)
            if self._turns_per_session
            else 0.0
        )
        avg_rec_lat = (
            sum(self._recognition_latencies_ms) / len(self._recognition_latencies_ms)
            if self._recognition_latencies_ms
            else 0.0
        )
        avg_think_lat = (
            sum(self._thinking_latencies_ms) / len(self._thinking_latencies_ms)
            if self._thinking_latencies_ms
            else 0.0
        )
        avg_speak_lat = (
            sum(self._speaking_latencies_ms) / len(self._speaking_latencies_ms)
            if self._speaking_latencies_ms
            else 0.0
        )

        return {
            "total_sessions": self.total_sessions,
            "total_barge_ins": self.total_barge_ins,
            "total_cancellations": self.total_cancellations,
            "total_recoveries": self.total_recoveries,
            "total_timeouts": self.total_timeouts,
            "total_errors": self.total_errors,
            "avg_session_duration_sec": round(avg_duration, 2),
            "avg_turns_per_session": round(avg_turns, 2),
            "avg_recognition_latency_ms": round(avg_rec_lat, 2),
            "avg_thinking_latency_ms": round(avg_think_lat, 2),
            "avg_speaking_latency_ms": round(avg_speak_lat, 2),
        }

    def reset(self) -> None:
        self._session_durations_sec.clear()
        self._turns_per_session.clear()
        self._recognition_latencies_ms.clear()
        self._thinking_latencies_ms.clear()
        self._speaking_latencies_ms.clear()
        self.total_sessions = 0
        self.total_barge_ins = 0
        self.total_cancellations = 0
        self.total_recoveries = 0
        self.total_timeouts = 0
        self.total_errors = 0


# Global singleton instance
orchestrator_metrics = OrchestratorMetrics()
