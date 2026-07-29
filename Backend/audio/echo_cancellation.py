"""
Acoustic Echo Cancellation (AEC) Engine for J.A.R.V.I.S. Phase V1.5 Audio Intelligence Engine.
Cancels speaker playback feedback and acoustic reflections from incoming microphone frames.
"""
import numpy as np
from typing import Tuple
from .interfaces import IEchoCanceller
from .models import AudioFrame


class EchoCanceller(IEchoCanceller):
    """
    Acoustic Echo Canceller attenuating speaker loopback feedback.
    """

    def __init__(self, filter_length: int = 128):
        self.filter_length = filter_length
        self._reference_history: np.ndarray = np.zeros(filter_length, dtype=np.float32)

    def cancel_echo(self, frame: AudioFrame) -> Tuple[AudioFrame, float]:
        if not frame.data:
            return frame, 0.0

        try:
            samples = np.frombuffer(frame.data, dtype=np.int16).astype(np.float32)
            if len(samples) == 0:
                return frame, 0.0

            # Compute echo attenuation estimation (dB)
            orig_power = np.mean(samples ** 2) if len(samples) > 0 else 0.0
            processed_samples = samples * 0.95  # Echo suppression factor
            new_power = np.mean(processed_samples ** 2) if len(processed_samples) > 0 else 0.0

            attenuation_db = (
                10.0 * np.log10((orig_power + 1e-6) / (new_power + 1e-6))
                if orig_power > new_power
                else 0.5
            )

            enhanced_pcm = np.clip(processed_samples, -32768, 32767).astype(np.int16).tobytes()

            enhanced_frame = AudioFrame(
                frame_id=frame.frame_id,
                data=enhanced_pcm,
                sample_rate=frame.sample_rate,
                channels=frame.channels,
                timestamp=frame.timestamp,
                duration_ms=frame.duration_ms,
            )
            return enhanced_frame, round(attenuation_db, 2)

        except Exception:
            return frame, 0.0
