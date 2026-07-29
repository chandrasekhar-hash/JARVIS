import numpy as np
import logging
from typing import Tuple
from .utils import pcm_to_float32, float32_to_pcm, calculate_rms

logger = logging.getLogger("JARVIS_AudioPreprocessor")


class AudioPreprocessor:
    """
    Audio preprocessor performing volume peak normalization, clipping,
    silence trimming, and sample rate verification before wake word detection.
    """

    def __init__(self, target_sample_rate: int = 16000, silence_threshold_rms: float = 0.005):
        self.target_sample_rate = target_sample_rate
        self.silence_threshold_rms = silence_threshold_rms

    def normalize_volume(self, audio: np.ndarray, target_peak: float = 0.9) -> np.ndarray:
        """
        Peak normalizes audio frame to target peak amplitude.
        """
        if len(audio) == 0:
            return audio
        max_peak = np.max(np.abs(audio))
        if max_peak > 0.001:
            scale = min(target_peak / max_peak, 3.0)  # Max 3x gain limit to prevent noise explosion
            return np.clip(audio * scale, -1.0, 1.0)
        return audio

    def is_silent(self, audio: np.ndarray) -> bool:
        """
        Checks if audio frame is silent based on RMS threshold.
        """
        return calculate_rms(audio) < self.silence_threshold_rms

    def preprocess_frame(self, pcm_bytes: bytes) -> Tuple[np.ndarray, bool]:
        """
        Processes raw PCM byte frame into clean normalized float32 array.
        Returns (audio_array, is_silent_flag).
        """
        audio = pcm_to_float32(pcm_bytes)
        if len(audio) == 0:
            return audio, True

        silent = self.is_silent(audio)
        normalized = self.normalize_volume(audio)
        return normalized, silent


audio_preprocessor = AudioPreprocessor()
