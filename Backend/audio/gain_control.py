"""
Automatic Gain Control (AGC) Engine for J.A.R.V.I.S. Phase V1.5 Audio Intelligence Engine.
Dynamically adjusts frame volume levels, compensates for distant speech, and prevents clipping.
"""
import numpy as np
from typing import Tuple
from .interfaces import IAutomaticGainController
from .models import AudioFrame


class AutomaticGainController(IAutomaticGainController):
    """
    Automatic Gain Controller optimizing dynamic range and target RMS energy.
    """

    def __init__(self, target_rms: float = 4000.0, max_gain_db: float = 24.0):
        self.target_rms = target_rms
        self.max_gain_factor = 10.0 ** (max_gain_db / 20.0)

    def apply_gain(self, frame: AudioFrame) -> Tuple[AudioFrame, float]:
        if not frame.data:
            return frame, 0.0

        try:
            samples = np.frombuffer(frame.data, dtype=np.int16).astype(np.float32)
            if len(samples) == 0:
                return frame, 0.0

            current_rms = np.sqrt(np.mean(samples ** 2)) if len(samples) > 0 else 0.0
            if current_rms < 10.0:  # Silence threshold
                return frame, 0.0

            desired_gain = self.target_rms / (current_rms + 1e-6)
            gain_factor = min(self.max_gain_factor, max(0.2, desired_gain))
            gain_applied_db = 20.0 * np.log10(gain_factor)

            scaled_samples = samples * gain_factor
            clipping_limit = 32767.0
            np.clip(scaled_samples, -clipping_limit, clipping_limit, out=scaled_samples)

            enhanced_pcm = scaled_samples.astype(np.int16).tobytes()

            enhanced_frame = AudioFrame(
                frame_id=frame.frame_id,
                data=enhanced_pcm,
                sample_rate=frame.sample_rate,
                channels=frame.channels,
                timestamp=frame.timestamp,
                duration_ms=frame.duration_ms,
            )
            return enhanced_frame, round(gain_applied_db, 2)

        except Exception:
            return frame, 0.0
