from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class WakeWordSettings(BaseModel):
    """
    Configuration settings for Wake Word Intelligence Engine.
    """
    enabled: bool = True
    primary_keyword: str = "jarvis"
    keywords: List[str] = Field(default_factory=lambda: ["jarvis", "hey jarvis", "computer", "nova", "friday"])
    aliases: Dict[str, List[str]] = Field(default_factory=lambda: {
        "jarvis": ["hey jarvis", "jarvis assistant", "yo jarvis"],
        "computer": ["hey computer"],
        "friday": ["hey friday"]
    })

    confidence_threshold: float = 0.75
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1280  # 80ms chunks at 16kHz
    buffer_seconds: float = 1.5

    noise_suppression_level: float = 0.8
    enable_agc: bool = True  # Automatic Gain Control
    highpass_cutoff: float = 80.0

    auto_recovery: bool = True
    recovery_cooldown_seconds: float = 2.0
    max_recovery_attempts: int = 10

    device_index: Optional[int] = None
    log_level: str = "INFO"


wake_word_settings = WakeWordSettings()
