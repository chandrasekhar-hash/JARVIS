"""
Phase V1.1 Wake Word Intelligence Engine Subsystem
"""
from .settings import WakeWordSettings, wake_word_settings
from .exceptions import WakeWordError, MicrophoneDisconnectedError
from .events import WakeWordDetectedEvent, WakeWordRejectedEvent
from .metrics import WakeWordMetrics, wake_word_metrics
from .keyword_manager import KeywordManager, keyword_manager
from .confidence import ConfidenceEngine, confidence_engine
from .audio_preprocessor import AudioPreprocessor, audio_preprocessor
from .noise_filter import NoiseFilter, noise_filter
from .detector import WakeWordDetector, wake_word_detector
from .listener import AudioListener, audio_listener
from .health import HealthMonitor, health_monitor
from .engine import WakeWordEngine, wake_word_engine

__all__ = [
    "WakeWordSettings", "wake_word_settings",
    "WakeWordError", "MicrophoneDisconnectedError",
    "WakeWordDetectedEvent", "WakeWordRejectedEvent",
    "WakeWordMetrics", "wake_word_metrics",
    "KeywordManager", "keyword_manager",
    "ConfidenceEngine", "confidence_engine",
    "AudioPreprocessor", "audio_preprocessor",
    "NoiseFilter", "noise_filter",
    "WakeWordDetector", "wake_word_detector",
    "AudioListener", "audio_listener",
    "HealthMonitor", "health_monitor",
    "WakeWordEngine", "wake_word_engine"
]
