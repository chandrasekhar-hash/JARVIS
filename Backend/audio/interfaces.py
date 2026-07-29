"""
Abstract Base Classes & Interfaces for J.A.R.V.I.S. Phase V1.5 Audio Intelligence Engine.
"""
from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any
from .models import (
    AudioFrame,
    AudioQualityReport,
    AudioConfidence,
)


class IAudioProcessor(ABC):
    """Abstract base interface for audio processors."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Processor identification name."""
        pass

    @abstractmethod
    def process(self, frame: AudioFrame) -> AudioFrame:
        """Processes and transforms an AudioFrame."""
        pass


class INoiseSuppressor(ABC):
    """Abstract interface for spectral background noise suppression."""

    @abstractmethod
    def suppress_noise(self, frame: AudioFrame) -> Tuple[AudioFrame, float]:
        """Suppresses noise and returns (enhanced_frame, snr_gain_db)."""
        pass


class IEchoCanceller(ABC):
    """Abstract interface for acoustic echo cancellation."""

    @abstractmethod
    def cancel_echo(self, frame: AudioFrame) -> Tuple[AudioFrame, float]:
        """Cancels speaker feedback and returns (enhanced_frame, echo_attenuation_db)."""
        pass


class IAutomaticGainController(ABC):
    """Abstract interface for automatic gain control (AGC)."""

    @abstractmethod
    def apply_gain(self, frame: AudioFrame) -> Tuple[AudioFrame, float]:
        """Applies dynamic gain adjustment and returns (enhanced_frame, gain_applied_db)."""
        pass


class IAudioNormalizer(ABC):
    """Abstract interface for peak and RMS amplitude normalization."""

    @abstractmethod
    def normalize(self, frame: AudioFrame) -> AudioFrame:
        """Normalizes audio frame amplitude levels."""
        pass


class IAudioQualityAnalyzer(ABC):
    """Abstract interface for audio signal quality scoring."""

    @abstractmethod
    def analyze_quality(self, frame: AudioFrame) -> AudioQualityReport:
        """Analyzes frame signal parameters and returns AudioQualityReport."""
        pass


class IAudioConfidenceEstimator(ABC):
    """Abstract interface for speech and environment confidence estimation."""

    @abstractmethod
    def estimate_confidence(
        self,
        frame: AudioFrame,
        quality_report: AudioQualityReport,
    ) -> AudioConfidence:
        """Estimates speech and acoustic environment confidence."""
        pass
