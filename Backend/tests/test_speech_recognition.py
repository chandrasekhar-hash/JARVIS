"""
Comprehensive Unit & Integration Test Suite for J.A.R.V.I.S. Phase V1.2 Speech Recognition Engine.
"""
import unittest
import asyncio
import time
import struct
from typing import List

from speech.config import SpeechConfig, speech_config
from speech.models import (
    AudioFrame,
    VADResult,
    STTResult,
    LanguageResult,
    EndpointResult,
    SpeechSession,
    SpeechState,
)
from speech.audio_sources import (
    MicrophoneSource,
    FileSource,
    WebSocketSource,
)
from speech.vad import (
    EnergySpectralVADEngine,
    SileroVADEngine,
    WebRTCVADEngine,
    VADEngineFactory,
)
from speech.streaming_stt import (
    MockStreamingSTTProvider,
    FasterWhisperProvider,
    GroqProvider,
    DeepgramProvider,
    OpenAIProvider,
    STTProviderFactory,
)
from speech.transcript_buffer import TranscriptBuffer
from speech.language_detector import LanguageDetector
from speech.endpoint_detector import EndpointDetector
from speech.punctuation import TranscriptCleaner
from speech.recovery import SpeechRecoveryManager
from speech.metrics import SpeechMetrics
from speech.events import (
    SpeechStartedEvent,
    SpeechPartialEvent,
    SpeechFinalEvent,
    SpeechCancelledEvent,
)
from speech.engine import SpeechRecognitionEngine
from brain.event_bus import EventBus
from conversation.engine import ConversationContinuityEngine


class TestSpeechRecognitionEngine(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.bus = EventBus()
        self.metrics = SpeechMetrics()

    def tearDown(self):
        self.loop.close()

    def _generate_pcm_data(self, duration_sec: float = 0.1, frequency: float = 440.0, sample_rate: int = 16000) -> bytes:
        """Generates synthetic audio PCM bytes for testing."""
        num_samples = int(sample_rate * duration_sec)
        samples = [int(10000 * (i % 32 / 32.0)) for i in range(num_samples)]
        return struct.pack(f"<{num_samples}h", *samples)

    def test_01_speech_config_and_factories(self):
        cfg = SpeechConfig(stt_provider="groq", vad_provider="webrtc")
        self.assertEqual(cfg.stt_provider, "groq")
        self.assertEqual(cfg.vad_provider, "webrtc")

        stt_instance = STTProviderFactory.create_provider("groq")
        self.assertIsInstance(stt_instance, GroqProvider)

        vad_instance = VADEngineFactory.create_vad_engine("webrtc")
        self.assertIsInstance(vad_instance, WebRTCVADEngine)

    def test_02_audio_sources(self):
        async def run_test():
            pcm_bytes = self._generate_pcm_data(0.2)
            file_src = FileSource(pcm_bytes)
            await file_src.start()
            self.assertTrue(file_src.is_active())

            frame = await file_src.read_frame()
            self.assertIsNotNone(frame)
            self.assertEqual(len(frame.data), 2048)
            await file_src.stop()

        self.loop.run_until_complete(run_test())

    def test_03_energy_spectral_vad(self):
        vad = EnergySpectralVADEngine(energy_threshold=0.01)
        pcm_bytes = self._generate_pcm_data(0.1, frequency=440.0)
        frame = AudioFrame(data=pcm_bytes, sample_rate=16000)

        res = vad.process_frame(frame)
        self.assertGreater(res.energy, 0.0)
        self.assertIsInstance(res, VADResult)

    def test_04_transcript_buffer_deduplication(self):
        buf = TranscriptBuffer()
        buf.add_partial("Jarvis what is")
        stable1 = buf.add_partial("what is the status")
        self.assertEqual(stable1, "Jarvis what is the status")

        final = buf.finalize()
        self.assertEqual(final, "Jarvis what is the status")

    def test_05_language_detector_cascades(self):
        ld = LanguageDetector()

        # Hindi script
        res_hi = ld.detect_language(b"", "नमस्ते जार्विस")
        self.assertEqual(res_hi.language, "hindi")
        self.assertFalse(res_hi.is_fallback)

        # Hinglish Romanized
        res_hinglish = ld.detect_language(b"", "mujhe apna kaam batao kaise karna hai")
        self.assertEqual(res_hinglish.language, "hinglish")

        # English
        res_en = ld.detect_language(b"", "Jarvis run diagnostic check")
        self.assertEqual(res_en.language, "english")

    def test_06_endpoint_detector(self):
        ed = EndpointDetector(min_pause_duration_ms=100.0, max_pause_duration_ms=200.0)
        vad_active = VADResult(is_speech=True, confidence=0.9, energy=0.1)
        res1 = ed.evaluate(vad_active, "Hello Jarvis")
        self.assertFalse(res1.is_endpoint)

        vad_silent = VADResult(is_speech=False, confidence=0.1, energy=0.0)
        ed.evaluate(vad_silent, "Hello Jarvis.")
        time.sleep(0.15)
        res2 = ed.evaluate(vad_silent, "Hello Jarvis.")
        self.assertTrue(res2.is_endpoint)

    def test_07_transcript_cleaner(self):
        cleaner = TranscriptCleaner()
        cleaned = cleaner.clean("  jarvis jarvis what is   the the status  ")
        self.assertEqual(cleaned, "Jarvis what is the status")

    def test_08_recovery_manager(self):
        async def run_test():
            rec = SpeechRecoveryManager(max_retries=2, retry_delay_sec=0.01)
            ok1 = await rec.handle_error(RuntimeError("mic stream dropped"), "s1")
            self.assertTrue(ok1)
            ok2 = await rec.handle_error(RuntimeError("mic stream dropped"), "s1")
            self.assertTrue(ok2)
            ok3 = await rec.handle_error(RuntimeError("mic stream dropped"), "s1")
            self.assertFalse(ok3)

        self.loop.run_until_complete(run_test())

    def test_09_master_speech_engine_lifecycle_and_events(self):
        async def run_test():
            emitted_events: List[str] = []

            def listener(evt):
                emitted_events.append(evt.name)

            self.bus.subscribe("speech_started", listener)
            self.bus.subscribe("speech_partial", listener)
            self.bus.subscribe("speech_final", listener)
            self.bus.subscribe("speech_cancelled", listener)

            pcm_bytes = self._generate_pcm_data(0.5) * 5
            file_src = FileSource(pcm_bytes)

            conv_engine = ConversationContinuityEngine(bus=self.bus)
            engine = SpeechRecognitionEngine(
                audio_source=file_src,
                stt_provider=MockStreamingSTTProvider(),
                bus=self.bus,
                conversation_engine=conv_engine,
            )

            session = await engine.start()
            self.assertEqual(session.state, SpeechState.LISTENING)

            # Wait for processing loop to ingest audio frames
            await asyncio.sleep(0.3)

            final_event = await engine.stop()
            self.assertIsNotNone(final_event)
            self.assertGreater(len(final_event.transcript), 0)

            # Verify metrics telemetry summary
            summary = engine.metrics.get_summary()
            self.assertGreater(summary["total_sessions"], 0)

        self.loop.run_until_complete(run_test())

    def test_10_speech_engine_cancel_support(self):
        async def run_test():
            emitted_events: List[str] = []

            def listener(evt):
                emitted_events.append(evt.name)

            self.bus.subscribe("speech_cancelled", listener)

            pcm_bytes = self._generate_pcm_data(0.5) * 5
            file_src = FileSource(pcm_bytes)

            engine = SpeechRecognitionEngine(
                audio_source=file_src,
                stt_provider=MockStreamingSTTProvider(),
                bus=self.bus,
            )

            session = await engine.start()
            await asyncio.sleep(0.05)

            await engine.cancel()
            self.assertIn("speech_cancelled", emitted_events)
            self.assertIsNone(engine.get_session())

        self.loop.run_until_complete(run_test())


if __name__ == "__main__":
    unittest.main()
