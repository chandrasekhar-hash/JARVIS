import numpy as np
from typing import Tuple


def pcm_to_float32(pcm_bytes: bytes) -> np.ndarray:
    """
    Converts 16-bit PCM byte buffer to a normalized float32 numpy array [-1.0, 1.0].
    """
    if not pcm_bytes:
        return np.array([], dtype=np.float32)
    int16_arr = np.frombuffer(pcm_bytes, dtype=np.int16)
    return int16_arr.astype(np.float32) / 32768.0


def float32_to_pcm(float_arr: np.ndarray) -> bytes:
    """
    Converts normalized float32 numpy array to 16-bit PCM bytes.
    """
    clipped = np.clip(float_arr, -1.0, 1.0)
    int16_arr = (clipped * 32767.0).astype(np.int16)
    return int16_arr.tobytes()


def calculate_rms(audio_frame: np.ndarray) -> float:
    """
    Calculates Root Mean Square (RMS) volume of an audio frame.
    """
    if len(audio_frame) == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(audio_frame))))


def compute_spectral_energy(audio_frame: np.ndarray) -> float:
    """
    Computes total spectral energy across frequency domain via FFT.
    """
    if len(audio_frame) == 0:
        return 0.0
    fft_vals = np.abs(np.fft.rfft(audio_frame))
    return float(np.sum(fft_vals))
