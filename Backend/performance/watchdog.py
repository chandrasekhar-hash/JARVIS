"""
Background Watchdog Timer for J.A.R.V.I.S. Phase V1.7.
Periodically scans for deadlocked tasks, stalled queues, hung workers, and missed heartbeats.
"""
import asyncio
import logging
from typing import Callable, Optional, Dict, Any

logger = logging.getLogger("JARVIS_WatchdogTimer")


class WatchdogTimer:
    """
    Background watchdog monitor scanning for hung tasks and deadlocks.
    """

    def __init__(self, interval_sec: float = 5.0, scan_callback: Optional[Callable] = None):
        self.interval_sec = interval_sec
        self.scan_callback = scan_callback

        self._task: Optional[asyncio.Task] = None
        self._running: bool = False
        self._stalled_detected: int = 0
        self._heartbeats: Dict[str, float] = {}

    def heartbeat(self, name: str) -> None:
        import time
        self._heartbeats[name] = time.time()

    async def start(self) -> None:
        self._running = True

        async def _loop():
            while self._running:
                try:
                    await asyncio.sleep(self.interval_sec)
                    if self.scan_callback:
                        if asyncio.iscoroutinefunction(self.scan_callback):
                            await self.scan_callback()
                        else:
                            self.scan_callback()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"[WatchdogTimer] Error during watchdog scan: {e}")

        self._task = asyncio.create_task(_loop())
        logger.info(f"[WatchdogTimer] Background watchdog started (interval: {self.interval_sec}s).")

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("[WatchdogTimer] Background watchdog stopped.")

    def get_summary(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "interval_sec": self.interval_sec,
            "stalled_detected": self._stalled_detected,
            "monitored_heartbeats": len(self._heartbeats),
        }
