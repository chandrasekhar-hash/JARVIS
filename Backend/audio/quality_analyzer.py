"""
Audio Quality Analysis Engine for J.A.R.V.I.S. Phase V1.5 Audio Intelligence Engine.
Computes SNR, speech energy, silence ratio, clipping percentage, background noise floor, and quality score.
"""
import numpy as np
from .interfaces import IAudioQualityAnalyzer
from .models import AudioFrame, AudioQualityReport


class AudioQualityAnalyzer(IAudioQualityAnalyzer):
    """
    Analyzes physical acoustic parameters of PCM audio frames.
    """

    def analyze_quality(self, frame: AudioFrame) -> AudioQualityReport:
        if not frame.data:
            return AudioQualityReport(quality_score=0.5)

        try:
            samples = np.frombuffer(frame.data, dtype=np.int16).astype(np.float32)
            if len(samples) == 0:
                return AudioQualityReport(quality_score=0.5)

            rms = float(np.sqrt(np.mean(samples ** 2)))
            peak = float(np.max(np.abs(samples)))

            # Clipping percentage: samples at max scale (>= 32760)
            clipping_count = int(np.sum(np.abs(samples) >= 32760))
            clipping_pct = (clipping_count / len(samples)) * 100.0 if len(samples) > 0 else 0.0

            # Silence ratio: samples below noise floor threshold
            silence_count = int(np.sum(np.abs(samples) < 300.0))
            silence_ratio = (silence_count / len(samples)) if len(samples) > 0 else 0.0

            # Background noise level and SNR estimation
            bg_noise_level = min(rms, 500.0)
            snr_db = 20.0 * np.log10((rms + 1e-6) / (bg_noise_level + 1e-6))

            # Composite Quality Score calculation (0.0 to 1.0)
            score = 1.0
            if clipping_pct > 1.0:
                score -= min(0.4, clipping_pct * 0.05)
            if snr_db < 5.0:
                score -= 0.2
            if rms < 100.0:
                score -= 0.2

            quality_score = max(0.0, min(1.0, score))

            return AudioQualityReport(
                snr_db=round(snr_db, 2),
                speech_energy=round(rms, 2),
                silence_ratio=round(silence_ratio, 3),
                clipping_percentage=round(clipping_pct, 2),
                background_noise_level=round(bg_noise_level, 2),
                quality_score=round(quality_score, 3),
            )

        except Exception:
            return AudioQualityReport(quality_score=0.5)
