"""
Audio Confidence Estimation Engine for J.A.R.V.I.S. Phase V1.5 Audio Intelligence Engine.
Estimates speech confidence, audio signal confidence, environment confidence, and combined confidence score.
"""
from .interfaces import IAudioConfidenceEstimator
from .models import AudioFrame, AudioQualityReport, AudioConfidence


class AudioConfidenceEstimator(IAudioConfidenceEstimator):
    """
    Confidence Estimator synthesizing acoustic quality metrics into unified confidence scores.
    """

    def estimate_confidence(
        self,
        frame: AudioFrame,
        quality_report: AudioQualityReport,
    ) -> AudioConfidence:
        if not quality_report:
            return AudioConfidence()

        # 1. Speech Confidence: higher speech energy & lower silence
        speech_conf = max(0.0, min(1.0, (quality_report.speech_energy / 5000.0) * (1.0 - quality_report.silence_ratio * 0.5)))

        # 2. Audio Confidence: driven by SNR and quality score
        audio_conf = max(0.0, min(1.0, quality_report.quality_score))

        # 3. Environment Confidence: penalized by background noise and clipping
        env_penalty = (quality_report.clipping_percentage * 0.05) + (quality_report.background_noise_level / 1000.0)
        env_conf = max(0.0, min(1.0, 1.0 - env_penalty))

        # 4. Combined Confidence Score
        combined = (0.4 * speech_conf) + (0.4 * audio_conf) + (0.2 * env_conf)

        return AudioConfidence(
            speech_confidence=round(speech_conf, 3),
            audio_confidence=round(audio_conf, 3),
            environment_confidence=round(env_conf, 3),
            combined_score=round(combined, 3),
        )
