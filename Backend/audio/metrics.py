"""
Metrics collection and telemetry tracker for J.A.R.V.I.S. Phase V1.5 Audio Intelligence Engine.
"""
from typing import Dict, Any, List


class AudioMetrics:
    """Tracks processing latency, noise reduction, AGC adjustments, quality scores, throughput, and errors."""

    def __init__(self, history_size: int = 100):
        self.history_size = history_size
        self._latencies_ms: List[float] = []
        self._snr_gains_db: List[float] = []
        self._gain_adjustments_db: List[float] = []
        self._quality_scores: List[float] = []
        self._confidence_scores: List[float] = []

        self.total_frames_processed: int = 0
        self.total_processing_failures: int = 0

    def record_latency(self, latency_ms: float) -> None:
        self._latencies_ms.append(latency_ms)
        if len(self._latencies_ms) > self.history_size:
            self._latencies_ms.pop(0)

    def record_snr_gain(self, snr_gain_db: float) -> None:
        self._snr_gains_db.append(snr_gain_db)
        if len(self._snr_gains_db) > self.history_size:
            self._snr_gains_db.pop(0)

    def record_gain_adjustment(self, gain_db: float) -> None:
        self._gain_adjustments_db.append(gain_db)
        if len(self._gain_adjustments_db) > self.history_size:
            self._gain_adjustments_db.pop(0)

    def record_quality_score(self, score: float) -> None:
        self._quality_scores.append(score)
        if len(self._quality_scores) > self.history_size:
            self._quality_scores.pop(0)

    def record_confidence_score(self, score: float) -> None:
        self._confidence_scores.append(score)
        if len(self._confidence_scores) > self.history_size:
            self._confidence_scores.pop(0)

    def get_summary(self) -> Dict[str, Any]:
        avg_latency = (
            sum(self._latencies_ms) / len(self._latencies_ms)
            if self._latencies_ms
            else 0.0
        )
        avg_snr_gain = (
            sum(self._snr_gains_db) / len(self._snr_gains_db)
            if self._snr_gains_db
            else 0.0
        )
        avg_gain_adj = (
            sum(self._gain_adjustments_db) / len(self._gain_adjustments_db)
            if self._gain_adjustments_db
            else 0.0
        )
        avg_quality = (
            sum(self._quality_scores) / len(self._quality_scores)
            if self._quality_scores
            else 1.0
        )
        avg_confidence = (
            sum(self._confidence_scores) / len(self._confidence_scores)
            if self._confidence_scores
            else 1.0
        )

        return {
            "total_frames_processed": self.total_frames_processed,
            "total_processing_failures": self.total_processing_failures,
            "avg_processing_latency_ms": round(avg_latency, 2),
            "avg_snr_gain_db": round(avg_snr_gain, 2),
            "avg_gain_adjustment_db": round(avg_gain_adj, 2),
            "avg_quality_score": round(avg_quality, 3),
            "avg_confidence_score": round(avg_confidence, 3),
        }

    def reset(self) -> None:
        self._latencies_ms.clear()
        self._snr_gains_db.clear()
        self._gain_adjustments_db.clear()
        self._quality_scores.clear()
        self._confidence_scores.clear()
        self.total_frames_processed = 0
        self.total_processing_failures = 0


# Global singleton instance
audio_metrics = AudioMetrics()
