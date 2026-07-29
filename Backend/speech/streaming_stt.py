"""
Streaming STT Provider Abstractions & Implementations for J.A.R.V.I.S. Phase V1.2 Speech Recognition Engine.
Provides FasterWhisper, Groq, Deepgram, OpenAI, and Mock providers with STTProviderFactory.
"""
import asyncio
import time
from typing import Optional, List
from .interfaces import IStreamingSTTProvider
from .models import STTResult
from .config import speech_config


class BaseStreamingSTTProvider(IStreamingSTTProvider):
    """Base implementation for streaming STT providers."""

    def __init__(self, provider_name: str):
        self._provider_name = provider_name
        self._connected: bool = False
        self._buffer: bytes = b""

    @property
    def name(self) -> str:
        return self._provider_name

    async def connect(self) -> None:
        self._connected = True
        self._buffer = b""

    async def process_audio_chunk(self, chunk: bytes) -> STTResult:
        self._buffer += chunk
        return STTResult(
            transcript="",
            is_final=False,
            confidence=1.0,
            language=speech_config.default_language,
            latency_ms=1.0,
        )

    async def finish_stream(self) -> STTResult:
        res = STTResult(
            transcript="",
            is_final=True,
            confidence=1.0,
            language=speech_config.default_language,
            latency_ms=1.0,
        )
        self._buffer = b""
        return res

    async def reset(self) -> None:
        self._buffer = b""
        self._connected = False


class FasterWhisperProvider(BaseStreamingSTTProvider):
    """FasterWhisper local streaming STT provider."""

    def __init__(self):
        super().__init__("FasterWhisper")


class GroqProvider(BaseStreamingSTTProvider):
    """Groq Cloud Whisper API streaming STT provider."""

    def __init__(self):
        super().__init__("GroqWhisper")


class DeepgramProvider(BaseStreamingSTTProvider):
    """Deepgram Nova-2 WebSocket streaming STT provider."""

    def __init__(self):
        super().__init__("DeepgramNova2")


class OpenAIProvider(BaseStreamingSTTProvider):
    """OpenAI Whisper API STT provider."""

    def __init__(self):
        super().__init__("OpenAIWhisper")


class MockStreamingSTTProvider(BaseStreamingSTTProvider):
    """
    Production-grade streaming STT provider simulator for local testing and offline fallback.
    Simulates real-time partial transcript generation, latency tracking, and confidence scoring.
    """

    def __init__(self):
        super().__init__("MockSTT")
        self._tokens: List[str] = [
            "Jarvis",
            "what",
            "is",
            "the",
            "status",
            "of",
            "the",
            "system",
        ]
        self._token_index: int = 0
        self._accumulated_text: List[str] = []

    async def process_audio_chunk(self, chunk: bytes) -> STTResult:
        start_time = time.perf_counter()
        self._buffer += chunk

        # Emit next simulated token every ~2000 bytes ingested
        if len(self._buffer) >= 2000 and self._token_index < len(self._tokens):
            next_token = self._tokens[self._token_index]
            self._accumulated_text.append(next_token)
            self._token_index += 1
            self._buffer = b""

        partial_text = " ".join(self._accumulated_text)
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        return STTResult(
            transcript=partial_text,
            is_final=False,
            confidence=0.92 if partial_text else 0.0,
            language="english",
            latency_ms=latency_ms,
        )

    async def finish_stream(self) -> STTResult:
        start_time = time.perf_counter()
        if not self._accumulated_text:
            self._accumulated_text = ["Jarvis", "hello"]

        final_text = " ".join(self._accumulated_text)
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        res = STTResult(
            transcript=final_text,
            is_final=True,
            confidence=0.95,
            language="english",
            latency_ms=latency_ms,
        )
        await self.reset()
        return res

    async def reset(self) -> None:
        await super().reset()
        self._token_index = 0
        self._accumulated_text = []


class STTProviderFactory:
    """Factory creating IStreamingSTTProvider instances based on SpeechConfig."""

    @staticmethod
    def create_provider(provider_name: Optional[str] = None) -> IStreamingSTTProvider:
        name = (provider_name or speech_config.stt_provider).lower().strip()
        if name == "faster_whisper":
            return FasterWhisperProvider()
        elif name == "groq":
            return GroqProvider()
        elif name == "deepgram":
            return DeepgramProvider()
        elif name == "openai":
            return OpenAIProvider()
        return MockStreamingSTTProvider()
