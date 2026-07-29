"""
Comprehensive Unit & Integration Test Suite for J.A.R.V.I.S. Phase V1.4 Voice Output Engine (TTS).
"""
import unittest
import asyncio
import time
from typing import List

from tts.config import VoiceConfig
from tts.models import VoiceProfile, PlaybackState, AudioChunk, TTSResult
from tts.interfaces import ITTSProvider, IAudioOutput
from tts.text_preprocessor import TextPreprocessor
from tts.sentence_segmenter import SentenceSegmenter
from tts.audio_cache import AudioCache
from tts.audio_outputs import (
    MockAudioOutput,
    DesktopSpeakerOutput,
    FileOutput,
    WebSocketOutput,
    MobileAudioOutput,
)
from tts.providers import (
    TTSProviderFactory,
    MockTTSProvider,
    EdgeTTSProvider,
    OpenAITTSProvider,
    strip_ssml_tags,
)
from tts.playback_engine import PlaybackEngine
from tts.metrics import VoiceMetrics, voice_metrics
from tts.engine import VoiceEngine
from brain.event_bus import EventBus


class TestVoiceEngineV14(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.bus = EventBus()
        voice_metrics.reset()

    def tearDown(self):
        self.loop.close()

    def test_01_text_preprocessor_normalization(self):
        tp = TextPreprocessor()
        raw = "Cost is $100 for 50% using AI and API at https://github.com/test"
        res = tp.preprocess(raw)
        self.assertIn("100 dollars", res)
        self.assertIn("50 percent", res)
        self.assertIn("A.I.", res)
        self.assertIn("A.P.I.", res)
        self.assertIn("github.com link", res)

    def test_02_sentence_segmenter_abbreviations(self):
        seg = SentenceSegmenter()
        text = "Dr. Smith met Mr. Jones. They discussed v1.4 release at 3.14 PM! Is it ready?"
        sentences = seg.segment(text)
        self.assertEqual(len(sentences), 3)
        self.assertIn("Dr. Smith met Mr. Jones.", sentences[0])
        self.assertIn("They discussed v1.4 release at 3.14 PM!", sentences[1])
        self.assertEqual("Is it ready?", sentences[2])

    def test_03_ssml_tag_stripping(self):
        ssml = "<speak><p>Hello <s>world</s></p></speak>"
        clean = strip_ssml_tags(ssml)
        self.assertEqual(clean, "Hello world")

    def test_04_provider_factory_and_swapping(self):
        p_mock = TTSProviderFactory.create_provider("mock")
        p_edge = TTSProviderFactory.create_provider("edge")
        p_openai = TTSProviderFactory.create_provider("openai")

        self.assertEqual(p_mock.name, "MockTTS")
        self.assertEqual(p_edge.name, "EdgeTTS")
        self.assertEqual(p_openai.name, "OpenAITTS")

    def test_05_audio_lru_cache(self):
        cache = AudioCache(max_size=2)
        res1 = TTSResult(session_id="s1", provider="mock", audio_data=b"123", audio_duration_ms=10.0)
        res2 = TTSResult(session_id="s2", provider="mock", audio_data=b"456", audio_duration_ms=20.0)
        res3 = TTSResult(session_id="s3", provider="mock", audio_data=b"789", audio_duration_ms=30.0)

        cache.put("k1", res1)
        cache.put("k2", res2)
        self.assertIsNotNone(cache.get("k1"))  # Hit

        cache.put("k3", res3)  # Evicts k2
        self.assertIsNone(cache.get("k2"))     # Miss
        self.assertIsNotNone(cache.get("k3"))  # Hit

    def test_06_audio_output_drivers(self):
        async def run_test():
            drivers: List[IAudioOutput] = [
                DesktopSpeakerOutput(),
                FileOutput("test.mp3"),
                WebSocketOutput(),
                MobileAudioOutput(),
                MockAudioOutput(),
            ]

            chunk = AudioChunk(data=b"PCM", is_final=True)

            for drv in drivers:
                await drv.start()
                self.assertTrue(drv.is_active())
                await drv.play_chunk(chunk)
                await drv.stop()
                self.assertFalse(drv.is_active())

        self.loop.run_until_complete(run_test())

    def test_07_voice_engine_speak_pipeline(self):
        async def run_test():
            engine = VoiceEngine(bus=self.bus)
            res = await engine.speak("System initialized successfully.")

            self.assertTrue(res.success)
            self.assertEqual(res.provider, "MockTTS")
            self.assertGreater(res.audio_duration_ms, 0.0)

        self.loop.run_until_complete(run_test())

    def test_08_playback_pause_resume_cancel(self):
        async def run_test():
            engine = VoiceEngine(bus=self.bus)
            session = await engine.stream("This is a long sentence testing pause, resume, and cancellation.")

            await asyncio.sleep(0.01)
            await engine.pause()
            self.assertEqual(session.state, PlaybackState.PAUSED)

            await engine.resume()
            self.assertEqual(session.state, PlaybackState.PLAYING)

            await engine.cancel()
            self.assertEqual(session.state, PlaybackState.CANCELLED)

        self.loop.run_until_complete(run_test())

    def test_09_event_bus_lifecycle_emission(self):
        async def run_test():
            emitted_events: List[str] = []

            def listener(evt):
                emitted_events.append(evt.name)

            self.bus.subscribe("SpeechSynthesisStarted", listener)
            self.bus.subscribe("SpeechChunkGenerated", listener)
            self.bus.subscribe("SpeechPlaybackStarted", listener)
            self.bus.subscribe("SpeechPlaybackCompleted", listener)

            engine = VoiceEngine(bus=self.bus)
            await engine.speak("Testing event lifecycle emission.")

            await asyncio.sleep(0.05)
            self.assertIn("SpeechSynthesisStarted", emitted_events)
            self.assertIn("SpeechChunkGenerated", emitted_events)
            self.assertIn("SpeechPlaybackStarted", emitted_events)
            self.assertIn("SpeechPlaybackCompleted", emitted_events)

        self.loop.run_until_complete(run_test())

    def test_10_dynamic_voice_switching(self):
        engine = VoiceEngine()
        self.assertEqual(engine.current_voice_profile.id, "en-US-JennyNeural")

        new_voice = VoiceProfile(
            id="en-US-GuyNeural",
            provider="EdgeTTS",
            language="english",
            gender="male",
            name="Guy Neural",
        )
        engine.set_voice(new_voice)
        self.assertEqual(engine.current_voice_profile.id, "en-US-GuyNeural")
        self.assertEqual(engine.current_voice_profile.gender, "male")

    def test_11_metrics_collection(self):
        async def run_test():
            engine = VoiceEngine(bus=self.bus)
            await engine.speak("First query metric test.")
            await engine.speak("Second query metric test.")

            metrics = engine.get_metrics()
            self.assertEqual(metrics["total_sessions"], 2)
            self.assertGreater(metrics["total_chunks"], 0)

        self.loop.run_until_complete(run_test())


if __name__ == "__main__":
    unittest.main()
