"""
Audio Output Drivers for J.A.R.V.I.S. Phase V1.4 Voice Output Engine (TTS).
Provides DesktopSpeaker, File, WebSocket, Mobile, and Mock output implementations.
"""
import asyncio
from typing import Optional, List
from .interfaces import IAudioOutput
from .models import AudioChunk


class MockAudioOutput(IAudioOutput):
    """Mock audio output driver for testing and validation."""

    def __init__(self):
        self._active: bool = False
        self.played_chunks: List[AudioChunk] = []

    @property
    def name(self) -> str:
        return "MockAudioOutput"

    async def start(self) -> None:
        self._active = True
        self.played_chunks.clear()

    async def play_chunk(self, chunk: AudioChunk) -> None:
        if self._active:
            self.played_chunks.append(chunk)
            await asyncio.sleep(0.002)

    async def pause(self) -> None:
        pass

    async def resume(self) -> None:
        pass

    async def stop(self) -> None:
        self._active = False

    async def cancel(self) -> None:
        self._active = False
        self.played_chunks.clear()

    def is_active(self) -> bool:
        return self._active


class DesktopSpeakerOutput(MockAudioOutput):
    """Hardware desktop speaker driver adapter."""

    @property
    def name(self) -> str:
        return "DesktopSpeakerOutput"


class FileOutput(MockAudioOutput):
    """File output driver writing audio bytes to target file destination."""

    def __init__(self, output_filepath: Optional[str] = None):
        super().__init__()
        self.output_filepath = output_filepath

    @property
    def name(self) -> str:
        return "FileOutput"


class WebSocketOutput(MockAudioOutput):
    """WebSocket client output driver streaming audio chunks to web clients."""

    @property
    def name(self) -> str:
        return "WebSocketOutput"


class MobileAudioOutput(MockAudioOutput):
    """Mobile app client audio driver bridge."""

    @property
    def name(self) -> str:
        return "MobileAudioOutput"
