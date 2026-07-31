"""
JARVIS Product 1.9 - Streaming Speech Coordinator.
Coordinates full-duplex streaming audio frames between hardware devices, V1.7 STT/TTS engines, and session buffers.
"""

import logging
from typing import Dict, Any, Generator
from .barge_in import BargeInManager

logger = logging.getLogger(__name__)


class StreamingSpeechCoordinator:
    def __init__(self, barge_in_manager: BargeInManager):
        self.barge_in_manager = barge_in_manager

    def stream_tts_audio_chunks(self, session_id: str, text_response: str) -> Generator[bytes, None, None]:
        words = text_response.split()
        for idx, word in enumerate(words):
            if self.barge_in_manager.is_session_interrupted(session_id):
                logger.info(f"[StreamingCoordinator] TTS streaming canceled mid-sentence at word '{word}' due to barge-in interrupt.")
                break
            
            chunk = f"audio_chunk_{idx}:{word}".encode("utf-8")
            yield chunk
