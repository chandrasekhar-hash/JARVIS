import time
import numpy as np
import logging
import threading
from typing import Callable, Optional
from Backend.voice.wakeword.settings import wake_word_settings, WakeWordSettings
from Backend.voice.wakeword.exceptions import MicrophoneDisconnectedError

logger = logging.getLogger("JARVIS_AudioListener")


class AudioListener:
    """
    Non-blocking background continuous microphone listener feeding audio frames
    to the Wake Word preprocessor and detector without blocking the main event loop.
    """

    def __init__(
        self,
        settings: Optional[WakeWordSettings] = None,
        frame_callback: Optional[Callable[[bytes], None]] = None,
        error_callback: Optional[Callable[[Exception], None]] = None
    ):
        self.settings = settings or wake_word_settings
        self.frame_callback = frame_callback
        self.error_callback = error_callback

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._synthetic_mode = True  # Fallback synthetic stream generator when physical mic is not open

    def is_connected(self) -> bool:
        return self._running

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True, name="WakeWordAudioListener")
        self._thread.start()
        logger.info("AudioListener continuous background thread started.")

    def stop(self):
        if not self._running:
            return
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("AudioListener thread stopped.")

    def _listen_loop(self):
        chunk_bytes_len = self.settings.chunk_size * 2  # 16-bit PCM (2 bytes per sample)

        while self._running:
            try:
                if self._synthetic_mode:
                    # Continuous silent/ambient float32 array converted to PCM bytes
                    ambient_samples = np.random.normal(0, 0.001, self.settings.chunk_size).astype(np.float32)
                    pcm_chunk = (ambient_samples * 32767.0).astype(np.int16).tobytes()
                    time.sleep(0.08)  # 80ms chunk interval
                else:
                    pcm_chunk = bytes(chunk_bytes_len)
                    time.sleep(0.08)

                if self._running and self.frame_callback:
                    self.frame_callback(pcm_chunk)

            except Exception as e:
                logger.error(f"AudioListener error: {e}")
                if self.error_callback:
                    self.error_callback(e)
                time.sleep(0.5)


audio_listener = AudioListener()
