"""
Configuration Layer for J.A.R.V.I.S. Phase V1.5 Audio Intelligence Engine.
Allows independent toggle and tuning of noise suppression, echo cancellation, automatic gain control (AGC),
PCM normalization, quality analysis, VAD refinement, and confidence estimation.
"""
from dataclasses import dataclass, field


@dataclass
class AudioConfig:
    """Centralized Audio Intelligence Engine Configuration."""
    noise_suppression_enabled: bool = True
    echo_cancellation_enabled: bool = True
    agc_enabled: bool = True
    normalization_enabled: bool = True
    vad_refinement_enabled: bool = True
    quality_analysis_enabled: bool = True
    confidence_estimation_enabled: bool = True

    sample_rate: int = 16000
    frame_size: int = 512
    silence_threshold: float = 0.01
    noise_threshold: float = 0.05
    target_rms_db: float = -16.0
    max_gain_db: float = 24.0
    max_processing_latency_ms: float = 20.0
    processing_pipeline_enabled: bool = True


# Global default audio configuration instance
audio_config = AudioConfig()
