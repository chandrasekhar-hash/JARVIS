"""
J.A.R.V.I.S. Phase V1.5 Audio Intelligence Engine Subsystem Package.
"""
from .config import AudioConfig, audio_config
from .models import (
    AudioFrame,
    EnhancedAudioFrame,
    AudioQualityReport,
    AudioConfidence,
    ProcessingResult,
    AudioStatistics,
    AudioSession,
)
from .interfaces import (
    IAudioProcessor,
    INoiseSuppressor,
    IEchoCanceller,
    IAutomaticGainController,
    IAudioNormalizer,
    IAudioQualityAnalyzer,
    IAudioConfidenceEstimator,
)
from .noise_suppression import NoiseSuppressor
from .echo_cancellation import EchoCanceller
from .gain_control import AutomaticGainController
from .normalization import AudioNormalizer
from .quality_analyzer import AudioQualityAnalyzer
from .confidence import AudioConfidenceEstimator
from .pipeline import AudioProcessingPipeline
from .metrics import AudioMetrics, audio_metrics
from .events import (
    AudioProcessingStarted,
    NoiseReductionCompleted,
    EchoCancellationCompleted,
    GainControlCompleted,
    AudioNormalizationCompleted,
    AudioQualityComputed,
    AudioConfidenceComputed,
    EnhancedAudioReady,
    AudioProcessingFailed,
)
from .engine import AudioIntelligenceEngine, audio_engine

__all__ = [
    "AudioConfig",
    "audio_config",
    "AudioFrame",
    "EnhancedAudioFrame",
    "AudioQualityReport",
    "AudioConfidence",
    "ProcessingResult",
    "AudioStatistics",
    "AudioSession",
    "IAudioProcessor",
    "INoiseSuppressor",
    "IEchoCanceller",
    "IAutomaticGainController",
    "IAudioNormalizer",
    "IAudioQualityAnalyzer",
    "IAudioConfidenceEstimator",
    "NoiseSuppressor",
    "EchoCanceller",
    "AutomaticGainController",
    "AudioNormalizer",
    "AudioQualityAnalyzer",
    "AudioConfidenceEstimator",
    "AudioProcessingPipeline",
    "AudioMetrics",
    "audio_metrics",
    "AudioProcessingStarted",
    "NoiseReductionCompleted",
    "EchoCancellationCompleted",
    "GainControlCompleted",
    "AudioNormalizationCompleted",
    "AudioQualityComputed",
    "AudioConfidenceComputed",
    "EnhancedAudioReady",
    "AudioProcessingFailed",
    "AudioIntelligenceEngine",
    "audio_engine",
]
