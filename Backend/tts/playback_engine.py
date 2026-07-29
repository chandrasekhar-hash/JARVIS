"""
Playback Engine for J.A.R.V.I.S. Phase V1.4 Voice Output Engine (TTS).
Manages audio chunk queue, playback loop, driver dispatch, pause/resume, and cancellation.
"""
import asyncio
import logging
from typing import Optional
from .interfaces import IPlaybackEngine, IAudioOutput
from .models import AudioChunk, PlaybackSession, PlaybackState
from .metrics import voice_metrics
from .audio_outputs import MockAudioOutput

logger = logging.getLogger("JARVIS_PlaybackEngine")


class PlaybackEngine(IPlaybackEngine):
    """
    Playback Engine managing streaming audio chunk queueing, low-latency driver dispatches,
    cancellation, and end-of-stream detection.
    """

    def __init__(self, output_driver: Optional[IAudioOutput] = None, max_queue_size: int = 100):
        self.output_driver = output_driver or MockAudioOutput()
        self.max_queue_size = max_queue_size
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._active_session: Optional[PlaybackSession] = None
        self._loop_task: Optional[asyncio.Task] = None
        self._paused: bool = False

    def set_output_driver(self, driver: IAudioOutput) -> None:
        """Updates active audio output driver dynamically."""
        self.output_driver = driver

    async def enqueue_chunk(self, chunk: AudioChunk) -> None:
        """Enqueues synthesized audio chunk for driver playback."""
        voice_metrics.total_chunks += 1
        await self._queue.put(chunk)

    async def start_playback(self, session: PlaybackSession) -> None:
        """Launches background playback loop for specified playback session."""
        self._active_session = session
        self._paused = False
        session.state = PlaybackState.PLAYING
        await self.output_driver.start()

        self._loop_task = asyncio.create_task(self._playback_loop(session))

    async def _playback_loop(self, session: PlaybackSession) -> None:
        """Core non-blocking loop consuming chunks from queue and playing via output driver."""
        try:
            while session.state in (PlaybackState.PLAYING, PlaybackState.PAUSED):
                if self._paused:
                    await asyncio.sleep(0.02)
                    continue

                try:
                    chunk: AudioChunk = await asyncio.wait_for(self._queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    if self._queue.empty() and session.state == PlaybackState.COMPLETED:
                        break
                    continue

                await self.output_driver.play_chunk(chunk)
                session.audio_chunks_count += 1

                if chunk.is_final and self._queue.empty():
                    session.state = PlaybackState.COMPLETED
                    break

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[PlaybackEngine] Error in playback loop for '{session.playback_id}': {e}")
            session.state = PlaybackState.ERROR
            voice_metrics.total_errors += 1

    async def pause(self) -> None:
        """Pauses active playback queue."""
        if self._active_session:
            self._paused = True
            self._active_session.state = PlaybackState.PAUSED
            await self.output_driver.pause()

    async def resume(self) -> None:
        """Resumes paused playback queue."""
        if self._active_session and self._paused:
            self._paused = False
            self._active_session.state = PlaybackState.PLAYING
            await self.output_driver.resume()

    async def stop(self) -> None:
        """Stops playback queue cleanly."""
        if self._active_session:
            self._active_session.state = PlaybackState.COMPLETED
            await self.output_driver.stop()

        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass

        self._drain_queue()

    async def cancel(self) -> None:
        """Immediately cancels playback queue and drains pending audio chunks."""
        voice_metrics.interruption_count += 1
        if self._active_session:
            self._active_session.state = PlaybackState.CANCELLED

        await self.output_driver.cancel()

        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass

        self._drain_queue()
        self._active_session = None

    def _drain_queue(self) -> None:
        """Clears pending queue items."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
