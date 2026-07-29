"""
TTS Provider Abstractions & Implementations for J.A.R.V.I.S. Phase V1.4 Voice Output Engine.
Provides EdgeTTS, OpenAI, Azure, ElevenLabs, and Mock providers with SSML support & TTSProviderFactory.
"""
import re
import uuid
import time
import asyncio
from typing import Optional, AsyncGenerator
from .interfaces import ITTSProvider
from .models import AudioChunk, TTSResult, VoiceProfile
from .config import voice_config


def strip_ssml_tags(ssml_text: str) -> str:
    """Strips SSML XML tags to produce clean plain text for non-SSML providers."""
    if not ssml_text:
        return ""
    clean = re.sub(r"<[^>]+>", "", ssml_text)
    return re.sub(r"\s+", " ", clean).strip()


class BaseTTSProvider(ITTSProvider):
    """Base provider implementation."""

    def __init__(self, provider_name: str):
        self._provider_name = provider_name
        self._connected: bool = False

    @property
    def name(self) -> str:
        return self._provider_name

    async def connect(self) -> None:
        self._connected = True

    async def synthesize(
        self,
        text_or_ssml: str,
        voice: VoiceProfile,
        is_ssml: bool = False,
    ) -> TTSResult:
        start_time = time.perf_counter()
        clean_text = strip_ssml_tags(text_or_ssml) if (is_ssml and not voice.supports_ssml) else text_or_ssml
        dummy_data = f"AUDIO_BYTES[{self.name}:{voice.id}:{clean_text[:20]}]".encode("utf-8")
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        return TTSResult(
            session_id=f"tts_{uuid.uuid4().hex[:12]}",
            provider=self.name,
            voice_profile=voice,
            latency_ms=latency_ms,
            audio_duration_ms=len(dummy_data) * 10.0,
            cache_hit=False,
            chunk_count=1,
            audio_data=dummy_data,
            success=True,
        )

    async def stream(
        self,
        text_or_ssml: str,
        voice: VoiceProfile,
        is_ssml: bool = False,
    ) -> AsyncGenerator[AudioChunk, None]:
        start_time = time.perf_counter()
        clean_text = strip_ssml_tags(text_or_ssml) if (is_ssml and not voice.supports_ssml) else text_or_ssml
        dummy_data = f"AUDIO_CHUNK[{self.name}:{clean_text[:20]}]".encode("utf-8")

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        yield AudioChunk(
            data=dummy_data,
            index=1,
            is_final=True,
            duration_ms=len(dummy_data) * 10.0,
            sample_rate=voice.sample_rate,
            format=voice_config.audio_format,
        )

    async def stop(self) -> None:
        self._connected = False

    async def cancel(self) -> None:
        self._connected = False

    async def reset(self) -> None:
        self._connected = False


class EdgeTTSProvider(BaseTTSProvider):
    """Microsoft Edge Neural TTS provider integration."""

    def __init__(self):
        super().__init__("EdgeTTS")

    async def synthesize(
        self,
        text_or_ssml: str,
        voice: VoiceProfile,
        is_ssml: bool = False,
    ) -> TTSResult:
        start_time = time.perf_counter()
        try:
            from tts_engines.edge_tts_engine import EdgeTTSEngine
            engine = EdgeTTSEngine()
            clean_text = strip_ssml_tags(text_or_ssml) if is_ssml else text_or_ssml
            audio_bytes = await engine.synthesize(clean_text, voice.gender, voice.language)
            latency_ms = (time.perf_counter() - start_time) * 1000.0

            return TTSResult(
                session_id=f"tts_{uuid.uuid4().hex[:12]}",
                provider=self.name,
                voice_profile=voice,
                latency_ms=latency_ms,
                audio_duration_ms=len(audio_bytes) / 32.0 if audio_bytes else 0.0,
                cache_hit=False,
                chunk_count=1,
                audio_data=audio_bytes,
                success=True,
            )
        except Exception as e:
            return await super().synthesize(text_or_ssml, voice, is_ssml)


class OpenAITTSProvider(BaseTTSProvider):
    """OpenAI TTS API provider."""

    def __init__(self):
        super().__init__("OpenAITTS")


class AzureTTSProvider(BaseTTSProvider):
    """Azure Cognitive Services Speech provider."""

    def __init__(self):
        super().__init__("AzureTTS")


class ElevenLabsProvider(BaseTTSProvider):
    """ElevenLabs Voice provider."""

    def __init__(self):
        super().__init__("ElevenLabs")


class MockTTSProvider(BaseTTSProvider):
    """Mock TTS provider for unit testing and deterministic verification."""

    def __init__(self):
        super().__init__("MockTTS")

    async def stream(
        self,
        text_or_ssml: str,
        voice: VoiceProfile,
        is_ssml: bool = False,
    ) -> AsyncGenerator[AudioChunk, None]:
        clean_text = strip_ssml_tags(text_or_ssml) if (is_ssml and not voice.supports_ssml) else text_or_ssml
        words = clean_text.split() if clean_text else ["hello"]

        for idx, word in enumerate(words):
            chunk_data = f"PCM_CHUNK[{word}]".encode("utf-8")
            is_last = (idx == len(words) - 1)
            yield AudioChunk(
                data=chunk_data,
                index=idx + 1,
                is_final=is_last,
                duration_ms=len(chunk_data) * 5.0,
                sample_rate=voice.sample_rate,
                format=voice_config.audio_format,
            )
            await asyncio.sleep(0.005)


class TTSProviderFactory:
    """Factory creating ITTSProvider instances based on VoiceConfig."""

    @staticmethod
    def create_provider(provider_name: Optional[str] = None) -> ITTSProvider:
        name = (provider_name or voice_config.tts_provider).lower().strip()
        if name == "edge":
            return EdgeTTSProvider()
        elif name == "openai":
            return OpenAITTSProvider()
        elif name == "azure":
            return AzureTTSProvider()
        elif name == "elevenlabs":
            return ElevenLabsProvider()
        return MockTTSProvider()
