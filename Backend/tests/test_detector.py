import unittest
import numpy as np
from Backend.voice.wakeword.keyword_manager import KeywordManager
from Backend.voice.wakeword.confidence import ConfidenceEngine
from Backend.voice.wakeword.detector import WakeWordDetector


class TestWakeWordDetector(unittest.TestCase):

    def setUp(self):
        self.kw_mgr = KeywordManager(primary_keyword="jarvis", keywords=["jarvis", "computer", "nova"])
        self.conf_eng = ConfidenceEngine(default_threshold=0.70)
        self.detector = WakeWordDetector(kw_manager=self.kw_mgr, conf_engine=self.conf_eng)

    def test_silent_frame_returns_none(self):
        silent_frame = np.zeros(1280, dtype=np.float32)
        match = self.detector.detect_in_frame(silent_frame)
        self.assertIsNone(match)

    def test_active_frame_detects_candidate(self):
        # Create non-silent audio frame with energy
        t = np.linspace(0, 0.08, 1280)
        audio_frame = (0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

        match = self.detector.detect_in_frame(audio_frame)
        self.assertIsNotNone(match)
        self.assertIn(match["keyword"], ["jarvis", "computer", "nova"])
        self.assertGreaterEqual(match["confidence"], 0.70)
        self.assertEqual(match["decision"], "ACTIVATE")


if __name__ == "__main__":
    unittest.main()
