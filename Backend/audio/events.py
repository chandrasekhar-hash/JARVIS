"""
Event payload definitions for J.A.R.V.I.S. Phase V1.5 Audio Intelligence Engine.
All events carry explicit session_id, frame_id, timestamps, and stage metadata.
"""
import time
from dataclasses import dataclass, field
from typing import Optional
from .models import EnhancedAudioFrame, AudioQualityReport, AudioConfidence


@dataclass
class AudioProcessingStarted:
    """Emitted when audio preprocessing commences for an audio frame."""
    session_id: str
    frame_id: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class NoiseReductionCompleted:
    """Emitted after noise suppression stage completes."""
    session_id: str
    frame_id: str
    snr_gain_db: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class EchoCancellationCompleted:
    """Emitted after acoustic echo cancellation completes."""
    session_id: str
    frame_id: str
    echo_attenuation_db: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class GainControlCompleted:
    """Emitted after automatic gain control (AGC) adjustment completes."""
    session_id: str
    frame_id: str
    gain_applied_db: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class AudioNormalizationCompleted:
    """Emitted after amplitude normalization completes."""
    session_id: str
    frame_id: str
    peak_normalized: bool = True
    timestamp: float = field(default_factory=time.time)


@dataclass
class AudioQualityComputed:
    """Emitted when audio signal quality analysis completes."""
    session_id: str
    frame_id: str
    quality_score: float = 1.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class AudioConfidenceComputed:
    """Emitted when speech/environment confidence estimation completes."""
    session_id: str
    frame_id: str
    combined_score: float = 1.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class EnhancedAudioReady:
    """Emitted when enhanced audio frame is ready for Speech Recognition (V1.2)."""
    session_id: str
    frame_id: str
    enhanced_frame: Optional[EnhancedAudioFrame] = None
    quality_report: Optional[AudioQualityReport] = None
    confidence: Optional[AudioConfidence] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class AudioProcessingFailed:
    """Emitted when an error occurs during audio pipeline processing."""
    session_id: str
    frame_id: str
    error_message: str = ""
    timestamp: float = field(default_factory=time.time)
