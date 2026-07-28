import unittest
import numpy as np
from Backend.voice.wakeword.audio_preprocessor import AudioPreprocessor
from Backend.voice.wakeword.noise_filter import NoiseFilter
from Backend.voice.wakeword.utils import calculate_rms


class TestAudioPreprocessorAndNoiseFilter(unittest.TestCase):

    def setUp(self):
        self.preprocessor = AudioPreprocessor()
        self.noise_filter = NoiseFilter(highpass_cutoff=80.0)

    def test_preprocessor_volume_normalization(self):
        # Create quiet frame
        t = np.linspace(0, 0.08, 1280)
        quiet_signal = (0.05 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

        normalized = self.preprocessor.normalize_volume(quiet_signal, target_peak=0.9)
        self.assertGreater(np.max(np.abs(normalized)), np.max(np.abs(quiet_signal)))

    def test_noise_filter_highpass_cutoff(self):
        # Create low frequency signal (30Hz) below 80Hz cutoff
        t = np.linspace(0, 0.5, 8000)
        low_freq_signal = (0.5 * np.sin(2 * np.pi * 30 * t)).astype(np.float32)

        filtered = self.noise_filter.filter_noise(low_freq_signal)
        orig_rms = calculate_rms(low_freq_signal)
        filtered_rms = calculate_rms(filtered)

        # RMS power should be reduced by at least 70% after zeroing out 30Hz fundamental
        self.assertLess(filtered_rms, orig_rms * 0.3)


if __name__ == "__main__":
    unittest.main()
