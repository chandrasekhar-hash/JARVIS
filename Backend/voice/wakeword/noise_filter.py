import numpy as np
import logging
from typing import Optional

logger = logging.getLogger("JARVIS_NoiseFilter")


class NoiseFilter:
    """
    Background Noise Filter handling fan noise, AC hum, keyboard clicks,
    room echo, and background conversations using spectral gating & high-pass filtering.
    """

    def __init__(self, suppression_level: float = 0.8, sample_rate: int = 16000, highpass_cutoff: float = 80.0):
        self.suppression_level = suppression_level
        self.sample_rate = sample_rate
        self.highpass_cutoff = highpass_cutoff
        self.noise_profile: Optional[np.ndarray] = None

    def update_noise_profile(self, silent_frame: np.ndarray):
        """
        Updates stationary background noise profile during silence intervals.
        """
        if len(silent_frame) == 0:
            return
        fft_frame = np.abs(np.fft.rfft(silent_frame))
        if self.noise_profile is None or len(self.noise_profile) != len(fft_frame):
            self.noise_profile = fft_frame
        else:
            # Exponential smoothing
            self.noise_profile = 0.9 * self.noise_profile + 0.1 * fft_frame

    def filter_noise(self, audio_frame: np.ndarray) -> np.ndarray:
        """
        Applies spectral gating noise reduction and high-pass filtering (>80Hz).
        """
        n = len(audio_frame)
        if n == 0:
            return audio_frame

        # 1. High-pass filter (>80Hz) via FFT
        fft = np.fft.rfft(audio_frame)
        freqs = np.fft.rfftfreq(n, d=1.0 / self.sample_rate)

        # Zero out frequencies below cutoff
        fft[freqs < self.highpass_cutoff] = 0.0

        # 2. Spectral gating if noise profile exists
        if self.noise_profile is not None and len(self.noise_profile) == len(fft):
            magnitude = np.abs(fft)
            phase = np.angle(fft)

            # Suppress magnitudes below noise profile threshold
            gate = magnitude > (self.noise_profile * self.suppression_level)
            gated_magnitude = magnitude * gate
            fft = gated_magnitude * np.exp(1j * phase)

        filtered = np.fft.irfft(fft, n=n)
        return np.clip(filtered, -1.0, 1.0)


noise_filter = NoiseFilter()
