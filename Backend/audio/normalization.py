"""
Audio Normalization Engine for J.A.R.V.I.S. Phase V1.5 Audio Intelligence Engine.
Performs peak amplitude and RMS normalization on PCM audio frames.
"""
import numpy as np
from .interfaces import IAudioNormalizer
from .models import AudioFrame


class AudioNormalizer(IAudioNormalizer):
    """
    Audio Normalizer standardizing amplitude range and peak scaling.
    """

    def __init__(self, target_peak_ratio: float = 0.90):
        self.target_peak = target_peak_ratio * 32767.0

    def normalize(self, frame: AudioFrame) -> AudioFrame:
        if not frame.data:
            return frame

        try:
            samples = np.frombuffer(frame.data, dtype=np.int16).astype(np.float32)
            if len(samples) == 0:
                return frame

            peak = np.max(np.abs(samples))
            if peak < 10.0:  # Silence
                return frame

            scale_factor = self.target_peak / (peak + 1e-6)
            normalized_samples = samples * min(scale_factor, 3.0)
            np.clip(normalized_samples, -32768, 32767, out=normalized_samples)

            normalized_pcm = normalized_samples.astype(np.int16).tobytes()

            return AudioFrame(
                frame_id=frame.frame_id,
                data=normalized_pcm,
                sample_rate=frame.sample_rate,
                channels=frame.channels,
                timestamp=frame.timestamp,
                duration_ms=frame.duration_ms,
            )

        except Exception:
            return frame
