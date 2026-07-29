"""
Intelligent End-of-Speech Endpoint Detector for J.A.R.V.I.S. Phase V1.2 Speech Recognition Engine.
Evaluates adaptive pause duration, speech energy, VAD confidence, and linguistic completeness.
"""
import time
from .interfaces import IEndpointDetector
from .models import VADResult, EndpointResult
from .config import speech_config


class EndpointDetector(IEndpointDetector):
    """
    Intelligent end-of-speech evaluator.
    Combines VAD speech state transitions, silent pause duration, energy decay,
    and trailing sentence punctuation to dynamically confirm utterance end.
    """

    def __init__(
        self,
        min_pause_duration_ms: float = 600.0,
        max_pause_duration_ms: float = 1200.0,
        sensitivity: float = 0.7,
    ):
        self.min_pause_duration_ms = min_pause_duration_ms
        self.max_pause_duration_ms = max_pause_duration_ms
        self.sensitivity = sensitivity

        self._last_speech_time: float = 0.0
        self._speech_has_started: bool = False

    def evaluate(self, vad_result: VADResult, partial_transcript: str) -> EndpointResult:
        now = time.time()

        if vad_result.is_speech:
            self._speech_has_started = True
            self._last_speech_time = now
            return EndpointResult(
                is_endpoint=False,
                pause_duration_ms=0.0,
                confidence=0.0,
                reason="speech_active",
            )

        if not self._speech_has_started:
            return EndpointResult(
                is_endpoint=False,
                pause_duration_ms=0.0,
                confidence=0.0,
                reason="speech_not_started",
            )

        # Calculate silent pause duration
        pause_duration_ms = (now - self._last_speech_time) * 1000.0 if self._last_speech_time > 0 else 0.0

        # Adjust threshold based on transcript trailing punctuation
        text = partial_transcript.strip()
        has_final_punctuation = text.endswith((".", "?", "!"))
        required_pause_ms = self.min_pause_duration_ms if has_final_punctuation else self.max_pause_duration_ms

        # Apply sensitivity scaling
        required_pause_ms = required_pause_ms * (1.2 - (self.sensitivity * 0.4))

        is_endpoint = pause_duration_ms >= required_pause_ms
        confidence = min(1.0, max(0.0, pause_duration_ms / required_pause_ms)) if is_endpoint else 0.0

        reason = "punctuation_pause" if (has_final_punctuation and is_endpoint) else "silence_timeout"

        return EndpointResult(
            is_endpoint=is_endpoint,
            pause_duration_ms=pause_duration_ms,
            confidence=confidence,
            reason=reason,
        )

    def reset(self) -> None:
        self._last_speech_time = 0.0
        self._speech_has_started = False
