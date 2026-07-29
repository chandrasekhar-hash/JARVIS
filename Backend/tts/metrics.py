"""
Metrics collection and telemetry tracker for J.A.R.V.I.S. Phase V1.4 Voice Output Engine (TTS).
"""
from typing import Dict, Any, List


class VoiceMetrics:
    """Tracks synthesis latency, first audio latency, playback latency, cache hits, and errors."""

    def __init__(self, history_size: int = 100):
        self.history_size = history_size
        self._synthesis_latencies_ms: List[float] = []
        self._first_audio_latencies_ms: List[float] = []
        self._playback_latencies_ms: List[float] = []
        self._audio_durations_sec: List[float] = []

        self.total_sessions: int = 0
        self.total_chunks: int = 0
        self.cache_hits: int = 0
        self.cache_misses: int = 0
        self.interruption_count: int = 0
        self.total_errors: int = 0

    def record_synthesis_latency(self, latency_ms: float) -> None:
        self._synthesis_latencies_ms.append(latency_ms)
        if len(self._synthesis_latencies_ms) > self.history_size:
            self._synthesis_latencies_ms.pop(0)

    def record_first_audio_latency(self, latency_ms: float) -> None:
        self._first_audio_latencies_ms.append(latency_ms)
        if len(self._first_audio_latencies_ms) > self.history_size:
            self._first_audio_latencies_ms.pop(0)

    def record_playback_latency(self, latency_ms: float) -> None:
        self._playback_latencies_ms.append(latency_ms)
        if len(self._playback_latencies_ms) > self.history_size:
            self._playback_latencies_ms.pop(0)

    def record_audio_duration(self, duration_sec: float) -> None:
        self._audio_durations_sec.append(duration_sec)
        if len(self._audio_durations_sec) > self.history_size:
            self._audio_durations_sec.pop(0)

    def get_summary(self) -> Dict[str, Any]:
        avg_synth_latency = (
            sum(self._synthesis_latencies_ms) / len(self._synthesis_latencies_ms)
            if self._synthesis_latencies_ms
            else 0.0
        )
        avg_first_audio_latency = (
            sum(self._first_audio_latencies_ms) / len(self._first_audio_latencies_ms)
            if self._first_audio_latencies_ms
            else 0.0
        )
        avg_playback_latency = (
            sum(self._playback_latencies_ms) / len(self._playback_latencies_ms)
            if self._playback_latencies_ms
            else 0.0
        )
        avg_duration = (
            sum(self._audio_durations_sec) / len(self._audio_durations_sec)
            if self._audio_durations_sec
            else 0.0
        )

        total_cache_reqs = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_cache_reqs) if total_cache_reqs > 0 else 0.0

        return {
            "total_sessions": self.total_sessions,
            "total_chunks": self.total_chunks,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": round(hit_rate, 3),
            "interruption_count": self.interruption_count,
            "total_errors": self.total_errors,
            "avg_synthesis_latency_ms": round(avg_synth_latency, 2),
            "avg_first_audio_latency_ms": round(avg_first_audio_latency, 2),
            "avg_playback_latency_ms": round(avg_playback_latency, 2),
            "avg_audio_duration_sec": round(avg_duration, 2),
        }

    def reset(self) -> None:
        self._synthesis_latencies_ms.clear()
        self._first_audio_latencies_ms.clear()
        self._playback_latencies_ms.clear()
        self._audio_durations_sec.clear()
        self.total_sessions = 0
        self.total_chunks = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.interruption_count = 0
        self.total_errors = 0


# Global singleton voice metrics instance
voice_metrics = VoiceMetrics()
