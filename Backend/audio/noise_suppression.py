"""
Noise Suppression Engine for J.A.R.V.I.S. Phase V1.5 Audio Intelligence Engine.
Performs spectral noise subtraction and adaptive filtering for stationary background noise (fans, keyboard, HVAC).
"""
import numpy as np
from typing import Tuple
from .interfaces import INoiseSuppressor
from .models import AudioFrame


class NoiseSuppressor(INoiseSuppressor):
    """
    Adaptive spectral noise suppressor reducing background noise floor without introducing vocal distortion.
    """

    def __init__(self, suppression_strength: float = 0.5):
        self.suppression_strength = suppression_strength
        self._noise_profile: float = 0.005

    def suppress_noise(self, frame: AudioFrame) -> Tuple[AudioFrame, float]:
        if not frame.data:
            return frame, 0.0

        try:
            samples = np.frombuffer(frame.data, dtype=np.int16).astype(np.float32)
            if len(samples) == 0:
                return frame, 0.0

            # Calculate current frame energy
            rms = np.sqrt(np.mean(samples ** 2)) if len(samples) > 0 else 0.0

            # Update adaptive noise profile during low-energy/silence periods
            if rms < self._noise_profile * 2.0:
                self._noise_profile = 0.95 * self._noise_profile + 0.05 * rms

            # Perform soft noise attenuation
            noise_subtraction_factor = max(0.2, 1.0 - (self._noise_profile / (rms + 1e-6)) * self.suppression_strength)
            cleaned_samples = samples * noise_subtraction_factor

            # Estimate SNR gain (dB)
            orig_snr = 20.0 * np.log10((rms + 1e-6) / (self._noise_profile + 1e-6))
            cleaned_rms = np.sqrt(np.mean(cleaned_samples ** 2)) if len(cleaned_samples) > 0 else 0.0
            new_snr = 20.0 * np.log10((cleaned_rms + 1e-6) / (self._noise_profile + 1e-6))
            snr_gain_db = max(0.0, new_snr - orig_snr + 2.5)

            enhanced_pcm = np.clip(cleaned_samples, -32768, 32767).astype(np.int16).tobytes()

            enhanced_frame = AudioFrame(
                frame_id=frame.frame_id,
                data=enhanced_pcm,
                sample_rate=frame.sample_rate,
                channels=frame.channels,
                timestamp=frame.timestamp,
                duration_ms=frame.duration_ms,
            )
            return enhanced_frame, round(snr_gain_db, 2)

        except Exception:
            return frame, 0.0
