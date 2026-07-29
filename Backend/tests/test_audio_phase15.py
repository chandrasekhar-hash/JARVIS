"""
Comprehensive Unit & Integration Test Suite for J.A.R.V.I.S. Phase V1.5 Audio Intelligence Engine.
"""
import unittest
import asyncio
import numpy as np
from typing import List

from audio.config import AudioConfig
from audio.models import AudioFrame, ProcessingResult, AudioQualityReport, AudioConfidence
from audio.noise_suppression import NoiseSuppressor
from audio.echo_cancellation import EchoCanceller
from audio.gain_control import AutomaticGainController
from audio.normalization import AudioNormalizer
from audio.quality_analyzer import AudioQualityAnalyzer
from audio.confidence import AudioConfidenceEstimator
from audio.pipeline import AudioProcessingPipeline
from audio.metrics import audio_metrics
from audio.engine import AudioIntelligenceEngine
from brain.event_bus import EventBus


class TestAudioEngineV15(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.bus = EventBus()
        audio_metrics.reset()

    def tearDown(self):
        self.loop.close()

    def _generate_pcm_frame(self, amplitude: float = 1000.0, length: int = 512) -> AudioFrame:
        samples = (np.sin(np.linspace(0, 2 * np.pi, length)) * amplitude).astype(np.int16)
        return AudioFrame(data=samples.tobytes(), duration_ms=20.0)

    def test_01_noise_suppression(self):
        ns = NoiseSuppressor()
        frame = self._generate_pcm_frame(amplitude=1500.0)
        enhanced_frame, snr_gain = ns.suppress_noise(frame)

        self.assertIsNotNone(enhanced_frame.data)
        self.assertGreaterEqual(snr_gain, 0.0)

    def test_02_echo_cancellation(self):
        ec = EchoCanceller()
        frame = self._generate_pcm_frame(amplitude=2000.0)
        enhanced_frame, attenuation = ec.cancel_echo(frame)

        self.assertIsNotNone(enhanced_frame.data)
        self.assertGreaterEqual(attenuation, 0.0)

    def test_03_automatic_gain_control(self):
        agc = AutomaticGainController(target_rms=4000.0)
        frame = self._generate_pcm_frame(amplitude=500.0)
        enhanced_frame, gain_db = agc.apply_gain(frame)

        self.assertIsNotNone(enhanced_frame.data)
        self.assertGreater(gain_db, 0.0)

    def test_04_audio_normalization(self):
        norm = AudioNormalizer(target_peak_ratio=0.90)
        frame = self._generate_pcm_frame(amplitude=5000.0)
        normalized = norm.normalize(frame)

        self.assertIsNotNone(normalized.data)

    def test_05_quality_analyzer(self):
        qa = AudioQualityAnalyzer()
        frame = self._generate_pcm_frame(amplitude=2000.0)
        report = qa.analyze_quality(frame)

        self.assertIsInstance(report, AudioQualityReport)
        self.assertGreater(report.quality_score, 0.0)

    def test_06_confidence_estimator(self):
        ce = AudioConfidenceEstimator()
        frame = self._generate_pcm_frame(amplitude=3000.0)
        report = AudioQualityReport(snr_db=15.0, speech_energy=3000.0, silence_ratio=0.1, quality_score=0.95)
        conf = ce.estimate_confidence(frame, report)

        self.assertIsInstance(conf, AudioConfidence)
        self.assertGreater(conf.combined_score, 0.0)

    def test_07_pipeline_execution(self):
        async def run_test():
            pipeline = AudioProcessingPipeline(bus=self.bus)
            frame = self._generate_pcm_frame(amplitude=1200.0)
            res = await pipeline.process_frame(frame)

            self.assertTrue(res.success)
            self.assertIsNotNone(res.enhanced_frame)
            self.assertIsNotNone(res.quality_report)
            self.assertIsNotNone(res.confidence)

        self.loop.run_until_complete(run_test())

    def test_08_event_lifecycle_emissions(self):
        async def run_test():
            emitted_events: List[str] = []

            def listener(evt):
                emitted_events.append(evt.name)

            self.bus.subscribe("AudioProcessingStarted", listener)
            self.bus.subscribe("NoiseReductionCompleted", listener)
            self.bus.subscribe("EnhancedAudioReady", listener)

            engine = AudioIntelligenceEngine(bus=self.bus)
            frame = self._generate_pcm_frame()
            await engine.process_frame(frame)

            self.assertIn("AudioProcessingStarted", emitted_events)
            self.assertIn("NoiseReductionCompleted", emitted_events)
            self.assertIn("EnhancedAudioReady", emitted_events)

        self.loop.run_until_complete(run_test())

    def test_09_stream_processing(self):
        async def run_test():
            engine = AudioIntelligenceEngine(bus=self.bus)

            async def generate_stream():
                for _ in range(5):
                    yield self._generate_pcm_frame()

            results = []
            async for res in engine.process_stream(generate_stream()):
                results.append(res)

            self.assertEqual(len(results), 5)
            self.assertTrue(all(r.success for r in results))

        self.loop.run_until_complete(run_test())

    def test_10_metrics_collection(self):
        async def run_test():
            engine = AudioIntelligenceEngine(bus=self.bus)
            for _ in range(3):
                await engine.process_frame(self._generate_pcm_frame())

            metrics = engine.get_metrics()
            self.assertEqual(metrics["total_frames_processed"], 3)
            self.assertGreater(metrics["avg_quality_score"], 0.0)

        self.loop.run_until_complete(run_test())


if __name__ == "__main__":
    unittest.main()
