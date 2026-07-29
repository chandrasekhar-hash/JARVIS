"""
Metrics collection and telemetry tracker for J.A.R.V.I.S. Phase V1.2 Speech Recognition Engine.
"""
import time
from typing import Dict, Any, List


class SpeechMetrics:
    """Tracks latency, confidence, speech duration, and quality metrics for STT pipeline."""

    def __init__(self, history_size: int = 100):
        self.history_size = history_size
        self._stt_latencies_ms: List[float] = []
        self._speech_durations_sec: List[float] = []
        self._confidence_scores: List[float] = []
        self._final_delays_ms: List[float] = []
        self._language_confidences: List[float] = []

        self.total_sessions: int = 0
        self.total_partials: int = 0
        self.total_finals: int = 0
        self.total_errors: int = 0
        self.total_cancellations: int = 0

    def record_stt_latency(self, latency_ms: float) -> None:
        """Records STT provider processing latency in ms."""
        self._stt_latencies_ms.append(latency_ms)
        if len(self._stt_latencies_ms) > self.history_size:
            self._stt_latencies_ms.pop(0)

    def record_speech_duration(self, duration_sec: float) -> None:
        """Records user speech utterance duration in seconds."""
        self._speech_durations_sec.append(duration_sec)
        if len(self._speech_durations_sec) > self.history_size:
            self._speech_durations_sec.pop(0)

    def record_confidence(self, confidence: float) -> None:
        """Records transcript confidence score (0.0 to 1.0)."""
        self._confidence_scores.append(confidence)
        if len(self._confidence_scores) > self.history_size:
            self._confidence_scores.pop(0)

    def record_final_delay(self, delay_ms: float) -> None:
        """Records final transcript delivery delay after speech end."""
        self._final_delays_ms.append(delay_ms)
        if len(self._final_delays_ms) > self.history_size:
            self._final_delays_ms.pop(0)

    def record_language_confidence(self, confidence: float) -> None:
        """Records language detection confidence."""
        self._language_confidences.append(confidence)
        if len(self._language_confidences) > self.history_size:
            self._language_confidences.pop(0)

    def get_summary(self) -> Dict[str, Any]:
        """Returns a snapshot summary of speech metrics telemetry."""
        avg_latency = (
            sum(self._stt_latencies_ms) / len(self._stt_latencies_ms)
            if self._stt_latencies_ms
            else 0.0
        )
        avg_confidence = (
            sum(self._confidence_scores) / len(self._confidence_scores)
            if self._confidence_scores
            else 0.0
        )
        avg_duration = (
            sum(self._speech_durations_sec) / len(self._speech_durations_sec)
            if self._speech_durations_sec
            else 0.0
        )
        avg_final_delay = (
            sum(self._final_delays_ms) / len(self._final_delays_ms)
            if self._final_delays_ms
            else 0.0
        )
        avg_lang_confidence = (
            sum(self._language_confidences) / len(self._language_confidences)
            if self._language_confidences
            else 0.0
        )

        return {
            "total_sessions": self.total_sessions,
            "total_partials": self.total_partials,
            "total_finals": self.total_finals,
            "total_errors": self.total_errors,
            "total_cancellations": self.total_cancellations,
            "avg_stt_latency_ms": round(avg_latency, 2),
            "avg_confidence": round(avg_confidence, 3),
            "avg_speech_duration_sec": round(avg_duration, 2),
            "avg_final_delay_ms": round(avg_final_delay, 2),
            "avg_language_confidence": round(avg_lang_confidence, 3),
        }

    def reset(self) -> None:
        """Resets telemetry metric counters."""
        self._stt_latencies_ms.clear()
        self._speech_durations_sec.clear()
        self._confidence_scores.clear()
        self._final_delays_ms.clear()
        self._language_confidences.clear()
        self.total_sessions = 0
        self.total_partials = 0
        self.total_finals = 0
        self.total_errors = 0
        self.total_cancellations = 0


# Global singleton metrics instance
speech_metrics = SpeechMetrics()
