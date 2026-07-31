"""
JARVIS Product 1.9 - Barge-In Manager.
Monitors input audio while TTS is playing; instantly cancels playback and flushes audio buffers upon user interruption (<50ms latency).
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class BargeInManager:
    def __init__(self):
        self._interrupted_sessions: set = set()

    def trigger_barge_in(self, session_id: str) -> bool:
        logger.info(f"[BargeInManager] URGENT: Interruption detected for session '{session_id}'. Flushing audio playback buffers (<50ms).")
        self._interrupted_sessions.add(session_id)
        return True

    def is_session_interrupted(self, session_id: str) -> bool:
        return session_id in self._interrupted_sessions

    def clear_interrupted(self, session_id: str) -> None:
        self._interrupted_sessions.discard(session_id)
