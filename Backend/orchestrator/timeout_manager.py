"""
Timeout Watchdog Manager for J.A.R.V.I.S. Phase V1.6 Voice Orchestrator.
Schedules and monitors wake, listening, conversation, idle, playback, and recovery timeouts.
"""
import asyncio
import logging
from typing import Dict, Optional, Callable
from .interfaces import ITimeoutManager

logger = logging.getLogger("JARVIS_TimeoutManager")


class TimeoutManager(ITimeoutManager):
    """
    Asynchronous timeout watchdog manager.
    """

    def __init__(self):
        self._timers: Dict[str, asyncio.Task] = {}

    @staticmethod
    def _make_key(session_id: str, timeout_type: str) -> str:
        return f"{session_id}:{timeout_type}"

    def start_timeout(self, session_id: str, timeout_type: str, timeout_sec: float, callback: Callable) -> None:
        key = self._make_key(session_id, timeout_type)
        self.cancel_timeout(session_id, timeout_type)

        async def _watchdog():
            try:
                await asyncio.sleep(timeout_sec)
                logger.warning(f"[TimeoutManager] Timeout '{timeout_type}' triggered for session '{session_id}' ({timeout_sec}s).")
                if asyncio.iscoroutinefunction(callback):
                    await callback(session_id, timeout_type)
                else:
                    callback(session_id, timeout_type)
            except asyncio.CancelledError:
                pass

        self._timers[key] = asyncio.create_task(_watchdog())

    def cancel_timeout(self, session_id: str, timeout_type: str) -> None:
        key = self._make_key(session_id, timeout_type)
        if key in self._timers:
            task = self._timers.pop(key)
            if not task.done():
                task.cancel()

    def cancel_all_for_session(self, session_id: str) -> None:
        prefix = f"{session_id}:"
        keys_to_cancel = [k for k in self._timers.keys() if k.startswith(prefix)]
        for k in keys_to_cancel:
            task = self._timers.pop(k)
            if not task.done():
                task.cancel()
