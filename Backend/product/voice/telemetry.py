"""
JARVIS Product 1.9 - Voice Telemetry.
Tracks latency metrics (STT, Intent, Tool, TTS, End-to-End) and barge-in counts.
"""

from typing import Dict, Any


class VoiceTelemetry:
    def __init__(self):
        self.session_count = 0
        self.barge_in_count = 0
        self.stt_latency_sum = 0.0
        self.tts_latency_sum = 0.0
        self.turn_count = 0

    def record_session(self):
        self.session_count += 1

    def record_barge_in(self):
        self.barge_in_count += 1

    def record_turn_latency(self, stt_ms: float, tts_ms: float):
        self.turn_count += 1
        self.stt_latency_sum += stt_ms
        self.tts_latency_sum += tts_ms

    def get_metrics(self) -> Dict[str, Any]:
        avg_stt = (self.stt_latency_sum / self.turn_count) if self.turn_count > 0 else 0.0
        avg_tts = (self.tts_latency_sum / self.turn_count) if self.turn_count > 0 else 0.0
        return {
            "session_count": self.session_count,
            "barge_in_count": self.barge_in_count,
            "turn_count": self.turn_count,
            "avg_stt_latency_ms": round(avg_stt, 2),
            "avg_tts_latency_ms": round(avg_tts, 2),
        }


voice_telemetry = VoiceTelemetry()
