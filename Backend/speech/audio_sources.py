"""
Audio Source implementations for J.A.R.V.I.S. Phase V1.2 Speech Recognition Engine.
Provides abstract audio ingestion implementations for Microphone, Audio Files, WebSockets, and Mobile streams.
"""
import asyncio
import time
from typing import Optional, List
from .interfaces import IAudioSource
from .models import AudioFrame


class MicrophoneSource(IAudioSource):
    """
    Local hardware microphone audio source.
    Pushes PCM audio frames asynchronously from local audio device queue.
    """

    def __init__(self, sample_rate: int = 16000, channels: int = 1, chunk_size: int = 1024):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self._active: bool = False
        self._queue: asyncio.Queue = asyncio.Queue()
        self._frame_counter: int = 0
        self._session_id: str = ""

    def set_session_id(self, session_id: str) -> None:
        """Sets active session ID for tagged audio frames."""
        self._session_id = session_id

    async def start(self) -> None:
        """Starts local microphone audio capture stream."""
        self._active = True
        self._frame_counter = 0

    async def push_pcm_data(self, data: bytes) -> None:
        """Pushes raw PCM bytes into audio queue (called by mic driver or simulation)."""
        if self._active:
            self._frame_counter += 1
            frame = AudioFrame(
                data=data,
                sample_rate=self.sample_rate,
                channels=self.channels,
                timestamp=time.time(),
                session_id=self._session_id,
                frame_index=self._frame_counter,
            )
            await self._queue.put(frame)

    async def read_frame(self) -> Optional[AudioFrame]:
        """Reads next available audio frame from microphone queue."""
        if not self._active:
            return None
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            return None

    async def stop(self) -> None:
        """Stops microphone stream and drains queue."""
        self._active = False
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    def is_active(self) -> bool:
        return self._active


class FileSource(IAudioSource):
    """
    Audio file reader source.
    Reads and streams PCM audio frames from audio file data or file path.
    """

    def __init__(self, audio_data: bytes, sample_rate: int = 16000, chunk_size: int = 2048):
        self.audio_data = audio_data
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self._offset: int = 0
        self._active: bool = False
        self._frame_counter: int = 0
        self._session_id: str = ""

    def set_session_id(self, session_id: str) -> None:
        self._session_id = session_id

    async def start(self) -> None:
        self._active = True
        self._offset = 0
        self._frame_counter = 0

    async def read_frame(self) -> Optional[AudioFrame]:
        if not self._active or self._offset >= len(self.audio_data):
            return None

        end = min(self._offset + self.chunk_size, len(self.audio_data))
        chunk = self.audio_data[self._offset:end]
        self._offset = end
        self._frame_counter += 1

        # Simulate real-time frame pacing (10ms per frame)
        await asyncio.sleep(0.005)

        return AudioFrame(
            data=chunk,
            sample_rate=self.sample_rate,
            channels=1,
            timestamp=time.time(),
            session_id=self._session_id,
            frame_index=self._frame_counter,
        )

    async def stop(self) -> None:
        self._active = False

    def is_active(self) -> bool:
        return self._active and self._offset < len(self.audio_data)


class WebSocketSource(IAudioSource):
    """
    WebSocket remote audio stream source.
    Accepts streamed audio frames from web/remote clients.
    """

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self._active: bool = False
        self._queue: asyncio.Queue = asyncio.Queue()
        self._frame_counter: int = 0
        self._session_id: str = ""

    def set_session_id(self, session_id: str) -> None:
        self._session_id = session_id

    async def start(self) -> None:
        self._active = True

    async def receive_ws_chunk(self, chunk: bytes) -> None:
        if self._active:
            self._frame_counter += 1
            frame = AudioFrame(
                data=chunk,
                sample_rate=self.sample_rate,
                channels=1,
                timestamp=time.time(),
                session_id=self._session_id,
                frame_index=self._frame_counter,
            )
            await self._queue.put(frame)

    async def read_frame(self) -> Optional[AudioFrame]:
        if not self._active:
            return None
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            return None

    async def stop(self) -> None:
        self._active = False

    def is_active(self) -> bool:
        return self._active


class MobileStreamSource(WebSocketSource):
    """Mobile application stream source bridge extending WebSocketSource."""
    pass
