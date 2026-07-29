"""
Configuration Layer for J.A.R.V.I.S. Phase V1.2 Speech Recognition Engine.
Allows dynamic selection of STT providers, VAD engines, language detection modes,
endpoint sensitivity, and confidence thresholds without code modification.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SpeechConfig:
    """Centralized Speech Recognition Engine Configuration."""
    stt_provider: str = "mock"  # Options: "faster_whisper", "groq", "deepgram", "openai", "mock"
    vad_provider: str = "energy_spectral"  # Options: "silero", "webrtc", "energy_spectral"
    language_detection_mode: str = "cascade"  # Options: "cascade", "provider_only", "fallback_only", "disabled"
    endpoint_sensitivity: float = 0.7  # Sensitivity scale 0.0 (lax) to 1.0 (strict)
    partial_transcript_interval_ms: float = 100.0
    confidence_threshold: float = 0.6
    streaming_enabled: bool = True
    sample_rate: int = 16000
    channels: int = 1
    chunk_size_bytes: int = 1024
    min_speech_duration_ms: float = 300.0
    max_pause_duration_ms: float = 1200.0
    default_language: str = "english"
    auto_punctuate: bool = True
    max_retries: int = 3
    retry_delay_sec: float = 0.5


# Global default configuration instance
speech_config = SpeechConfig()
