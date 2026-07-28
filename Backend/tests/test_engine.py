import unittest
import numpy as np
import time
from Backend.voice.wakeword.engine import WakeWordEngine
from Backend.voice.wakeword.settings import WakeWordSettings
from Backend.voice.wakeword.keyword_manager import KeywordManager


class TestWakeWordEngine(unittest.TestCase):

    def setUp(self):
        self.settings = WakeWordSettings(confidence_threshold=0.70)
        self.kw_mgr = KeywordManager(primary_keyword="jarvis")
        self.engine = WakeWordEngine(settings=self.settings, kw_manager=self.kw_mgr)

    def tearDown(self):
        if self.engine._is_running:
            self.engine.stop()

    def test_engine_lifecycle_start_stop_restart(self):
        self.assertFalse(self.engine._is_running)
        self.engine.start()
        self.assertTrue(self.engine._is_running)

        health = self.engine.get_health()
        self.assertEqual(health["status"], "RUNNING")
        self.assertTrue(health["microphone_connected"])

        self.engine.stop()
        self.assertFalse(self.engine._is_running)
        self.assertEqual(self.engine.get_health()["status"], "STOPPED")

    def test_pcm_frame_processing_and_callback(self):
        detected_events = []

        def on_detection(meta):
            detected_events.append(meta)

        self.engine.register_detection_callback(on_detection)
        self.engine.start()

        # Generate active audio PCM frame
        t = np.linspace(0, 0.08, 1280)
        float_samples = (0.25 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        int16_samples = (float_samples * 32767.0).astype(np.int16)
        pcm_bytes = int16_samples.tobytes()

        res = self.engine.process_pcm_frame(pcm_bytes)
        self.assertIsNotNone(res)
        self.assertEqual(len(detected_events), 1)
        self.assertEqual(detected_events[0]["keyword"], "jarvis")


if __name__ == "__main__":
    unittest.main()
