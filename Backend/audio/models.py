"""
Data models and data structures for J.A.R.V.I.S. Phase V1.5 Audio Intelligence Engine.
Includes AudioFrame, EnhancedAudioFrame, AudioQualityReport, AudioStatistics, AudioSession,
ProcessingResult, and AudioConfidence.
"""
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class AudioFrame:
    """Represents a raw input PCM audio frame."""
    frame_id: str = field(default_factory=lambda: f"frm_{uuid.uuid4().hex[:12]}")
    data: bytes = b""
    sample_rate: int = 16000
    channels: int = 1
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0


@dataclass
class EnhancedAudioFrame:
    """Represents a processed/enhanced audio frame."""
    frame_id: str
    original_frame: AudioFrame
    enhanced_data: bytes = b""
    snr_db: float = 0.0
    rms_level: float = 0.0
    gain_applied_db: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class AudioQualityReport:
    """Audio signal quality breakdown report."""
    snr_db: float = 0.0
    speech_energy: float = 0.0
    silence_ratio: float = 0.0
    clipping_percentage: float = 0.0
    background_noise_level: float = 0.0
    quality_score: float = 1.0  # 0.0 to 1.0 score scale


@dataclass
class AudioConfidence:
    """Confidence estimation for speech and acoustic environment."""
    speech_confidence: float = 1.0
    audio_confidence: float = 1.0
    environment_confidence: float = 1.0
    combined_score: float = 1.0


@dataclass
class ProcessingResult:
    """Output struct returned by the audio processing pipeline."""
    success: bool = True
    frame_id: str = ""
    enhanced_frame: Optional[EnhancedAudioFrame] = None
    quality_report: Optional[AudioQualityReport] = None
    confidence: Optional[AudioConfidence] = None
    error: Optional[str] = None


@dataclass
class AudioStatistics:
    """Cumulative statistics for audio processing telemetry."""
    total_frames_processed: int = 0
    avg_snr_db: float = 0.0
    avg_quality_score: float = 0.0
    total_clipping_events: int = 0


@dataclass
class AudioSession:
    """Tracks state and quality metrics for an active audio stream session."""
    session_id: str = field(default_factory=lambda: f"aud_{uuid.uuid4().hex[:12]}")
    started_at: float = field(default_factory=time.time)
    frames_count: int = 0
    quality_reports: List[AudioQualityReport] = field(default_factory=list)
