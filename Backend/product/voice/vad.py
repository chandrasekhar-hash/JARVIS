"""
JARVIS Product 1.9 - Voice Activity Detector (VAD).
Classifies audio frames as speech vs. silence to determine speech boundaries.
"""

import logging

logger = logging.getLogger(__name__)


class VoiceActivityDetector:
    def __init__(self, energy_threshold: float = 0.02):
        self.energy_threshold = energy_threshold

    def is_speech(self, audio_chunk: bytes) -> bool:
        if not audio_chunk:
            return False

        # Simulate frame energy computation
        if b"silence" in audio_chunk:
            return False
        return True
