"""
Phase V1.1 Wake Word Intelligence Engine Subsystem
"""
from Backend.voice.wakeword.settings import WakeWordSettings, wake_word_settings
from Backend.voice.wakeword.exceptions import WakeWordError, MicrophoneDisconnectedError
from Backend.voice.wakeword.events import WakeWordDetectedEvent, WakeWordRejectedEvent
from Backend.voice.wakeword.metrics import WakeWordMetrics, wake_word_metrics
from Backend.voice.wakeword.keyword_manager import KeywordManager, keyword_manager
from Backend.voice.wakeword.confidence import ConfidenceEngine, confidence_engine
from Backend.voice.wakeword.audio_preprocessor import AudioPreprocessor, audio_preprocessor
from Backend.voice.wakeword.noise_filter import NoiseFilter, noise_filter
from Backend.voice.wakeword.detector import WakeWordDetector, wake_word_detector
from Backend.voice.wakeword.listener import AudioListener, audio_listener
from Backend.voice.wakeword.health import HealthMonitor, health_monitor
from Backend.voice.wakeword.engine import WakeWordEngine, wake_word_engine

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
