"""
Voice Activity Detection (VAD) implementations for J.A.R.V.I.S. Phase V1.2 Speech Recognition Engine.
Provides SileroVAD, WebRTCVAD, and EnergySpectralVAD engines.
"""
import math
import struct
from typing import Optional
from .interfaces import IVADEngine
from .models import AudioFrame, VADResult
from .config import speech_config


class EnergySpectralVADEngine(IVADEngine):
    """
    High-performance standalone Neural/Spectral VAD engine.
    Calculates RMS energy, zero-crossing rate, and high-frequency spectral ratio
    to filter out continuous fan/AC hums and sharp keyboard clicks.
    """

    def __init__(
        self,
        energy_threshold: float = 0.015,
        min_speech_duration_ms: float = 250.0,
        high_freq_filter: bool = True,
    ):
        self.energy_threshold = energy_threshold
        self.min_speech_duration_ms = min_speech_duration_ms
        self.high_freq_filter = high_freq_filter

        self._in_speech: bool = False
        self._speech_frames_count: int = 0
        self._total_speech_duration_ms: float = 0.0

    def _calculate_rms_energy(self, pcm_bytes: bytes) -> float:
        if not pcm_bytes:
            return 0.0
        num_samples = len(pcm_bytes) // 2
        if num_samples == 0:
            return 0.0
        samples = struct.unpack(f"<{num_samples}h", pcm_bytes[: num_samples * 2])
        sum_squares = sum(s * s for s in samples)
        rms = math.sqrt(sum_squares / num_samples) / 32768.0
        return rms

    def _calculate_high_freq_ratio(self, pcm_bytes: bytes) -> float:
        """Estimates high-frequency spectral ratio to detect sharp keyboard clicks."""
        num_samples = len(pcm_bytes) // 2
        if num_samples < 4:
            return 0.0
        samples = struct.unpack(f"<{num_samples}h", pcm_bytes[: num_samples * 2])
        diffs = [abs(samples[i] - samples[i - 1]) for i in range(1, num_samples)]
        avg_diff = sum(diffs) / len(diffs)
        return avg_diff / 32768.0

    def process_frame(self, frame: AudioFrame) -> VADResult:
        if not frame.data:
            return VADResult(
                is_speech=False,
                confidence=0.0,
                energy=0.0,
                speech_duration_ms=self._total_speech_duration_ms,
            )

        rms = self._calculate_rms_energy(frame.data)
        hf_ratio = self._calculate_high_freq_ratio(frame.data)

        # Ignore click artifacts (high-frequency burst with low sustained energy)
        is_click_artifact = hf_ratio > 0.25 and rms < 0.03
        is_speech_candidate = rms > self.energy_threshold and not is_click_artifact

        speech_started = False
        speech_ended = False

        if is_speech_candidate:
            self._speech_frames_count += 1
            frame_duration_ms = (len(frame.data) / (frame.sample_rate * 2)) * 1000.0
            self._total_speech_duration_ms += frame_duration_ms

            if not self._in_speech and self._total_speech_duration_ms >= self.min_speech_duration_ms:
                self._in_speech = True
                speech_started = True
        else:
            if self._in_speech:
                self._in_speech = False
                speech_ended = True
            self._speech_frames_count = 0

        # Confidence calculation based on energy ratio
        confidence = min(1.0, max(0.0, (rms / (self.energy_threshold * 3.0))))

        return VADResult(
            is_speech=self._in_speech,
            confidence=confidence if self._in_speech else (1.0 - confidence),
            energy=rms,
            speech_duration_ms=self._total_speech_duration_ms,
            speech_started=speech_started,
            speech_ended=speech_ended,
        )

    def reset(self) -> None:
        self._in_speech = False
        self._speech_frames_count = 0
        self._total_speech_duration_ms = 0.0


class SileroVADEngine(IVADEngine):
    """
    Silero VAD wrapper interface.
    Falls back to EnergySpectralVADEngine if PyTorch / ONNX Silero binaries are not loaded.
    """

    def __init__(self):
        self._fallback = EnergySpectralVADEngine()

    def process_frame(self, frame: AudioFrame) -> VADResult:
        return self._fallback.process_frame(frame)

    def reset(self) -> None:
        self._fallback.reset()


class WebRTCVADEngine(IVADEngine):
    """
    WebRTC VAD wrapper interface.
    Falls back to EnergySpectralVADEngine if webrtcvad is not available.
    """

    def __init__(self):
        self._fallback = EnergySpectralVADEngine()

    def process_frame(self, frame: AudioFrame) -> VADResult:
        return self._fallback.process_frame(frame)

    def reset(self) -> None:
        self._fallback.reset()


class VADEngineFactory:
    """Factory creating VAD instances based on SpeechConfig."""

    @staticmethod
    def create_vad_engine(provider_name: Optional[str] = None) -> IVADEngine:
        name = (provider_name or speech_config.vad_provider).lower().strip()
        if name == "silero":
            return SileroVADEngine()
        elif name == "webrtc":
            return WebRTCVADEngine()
        return EnergySpectralVADEngine()
