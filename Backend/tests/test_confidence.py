import unittest
from Backend.voice.wakeword.confidence import ConfidenceEngine


class TestConfidenceEngine(unittest.TestCase):

    def setUp(self):
        self.engine = ConfidenceEngine(default_threshold=0.75)

    def test_high_confidence_match_activates(self):
        activated, meta = self.engine.evaluate_match(
            keyword="jarvis",
            raw_score=0.85,
            audio_duration=0.5,
            energy_level=0.05
        )
        self.assertTrue(activated)
        self.assertEqual(meta["decision"], "ACTIVATE")
        self.assertGreaterEqual(meta["confidence"], 0.75)

    def test_low_confidence_match_rejects(self):
        activated, meta = self.engine.evaluate_match(
            keyword="jarvis",
            raw_score=0.50,
            audio_duration=0.5,
            energy_level=0.005
        )
        self.assertFalse(activated)
        self.assertEqual(meta["decision"], "REJECT")

    def test_dynamic_threshold_update(self):
        self.engine.set_threshold(0.60)
        self.assertEqual(self.engine.threshold, 0.60)

        activated, meta = self.engine.evaluate_match(
            keyword="computer",
            raw_score=0.65,
            audio_duration=0.5,
            energy_level=0.03
        )
        self.assertTrue(activated)


if __name__ == "__main__":
    unittest.main()
