"""
Configuration Layer for J.A.R.V.I.S. Phase V1.4 Voice Output Engine (TTS).
Allows dynamic selection of TTS providers, output drivers, voice profiles, audio formatting,
streaming options, and LRU cache sizing without code modification.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class VoiceConfig:
    """Centralized Voice Output Engine Configuration."""
    tts_provider: str = "mock"  # Options: "edge", "openai", "azure", "elevenlabs", "mock"
    output_driver: str = "mock"  # Options: "desktop_speaker", "file", "websocket", "mobile", "mock"
    default_voice_id: str = "en-US-JennyNeural"
    default_language: str = "english"
    default_gender: str = "female"
    speech_rate: float = 1.0  # Speed multiplier (e.g. 0.8 to 1.5)
    pitch: float = 1.0        # Pitch multiplier
    volume: float = 1.0       # Volume scale (0.0 to 1.0)
    streaming_enabled: bool = True
    audio_format: str = "mp3"  # "mp3", "pcm", "wav", "ogg"
    sample_rate: int = 24000
    cache_enabled: bool = True
    cache_size: int = 100
    max_queue_size: int = 100
    playback_timeout_sec: float = 30.0
    buffer_size_bytes: int = 4096
    voice_fallback_enabled: bool = True
    preprocess_text: bool = True


# Global default voice configuration instance
voice_config = VoiceConfig()
