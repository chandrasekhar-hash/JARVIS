"""
Automatic Failure Recovery Manager for J.A.R.V.I.S. Phase V1.2 Speech Recognition Engine.
"""
import asyncio
import logging
from typing import Dict
from .interfaces import ISpeechRecoveryManager
from .metrics import speech_metrics

logger = logging.getLogger("JARVIS_SpeechRecovery")


class SpeechRecoveryManager(ISpeechRecoveryManager):
    """
    Manages automatic recovery from microphone disconnects, STT provider timeouts, and network errors.
    Enforces exponential backoff retries without crashing the application process.
    """

    def __init__(self, max_retries: int = 3, retry_delay_sec: float = 0.5):
        self.max_retries = max_retries
        self.retry_delay_sec = retry_delay_sec
        self._retry_counts: Dict[str, int] = {}

    async def handle_error(self, error: Exception, session_id: str) -> bool:
        """Attempts automatic recovery for the specified session ID."""
        current_retries = self._retry_counts.get(session_id, 0)
        speech_metrics.total_errors += 1

        if current_retries >= self.max_retries:
            logger.error(
                f"[SpeechRecovery] Session '{session_id}' exceeded max retries ({self.max_retries}). Error: {error}"
            )
            return False

        self._retry_counts[session_id] = current_retries + 1
        backoff_sec = self.retry_delay_sec * (2 ** current_retries)
        logger.warning(
            f"[SpeechRecovery] Session '{session_id}' retry {current_retries + 1}/{self.max_retries} in {backoff_sec:.2f}s after error: {error}"
        )

        await asyncio.sleep(backoff_sec)
        return True

    def reset(self) -> None:
        self._retry_counts.clear()
