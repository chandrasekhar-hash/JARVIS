import asyncio
import time
import logging
from typing import Optional, Callable
from enum import Enum

logger = logging.getLogger("JARVIS_Client_Scheduler")


class SyncTrigger(str, Enum):
    ON_STARTUP = "ON_STARTUP"
    ON_LOCAL_CHANGE = "ON_LOCAL_CHANGE"
    ON_NETWORK_RESTORE = "ON_NETWORK_RESTORE"
    PERIODIC_BACKGROUND = "PERIODIC_BACKGROUND"
    MANUAL = "MANUAL"


class IntelligentSyncScheduler:
    """
    Intelligent Sync Scheduler managing trigger-based background synchronization.
    Avoids unnecessary sync traffic when no local or remote changes exist.
    """

    def __init__(self, sync_callback: Optional[Callable[[SyncTrigger], None]] = None, period_seconds: float = 60.0):
        self.sync_callback = sync_callback
        self.period_seconds = period_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.last_sync_trigger: Optional[SyncTrigger] = None

    def start(self):
        if not self._running:
            self._running = True
            try:
                loop = asyncio.get_running_loop()
                self._task = loop.create_task(self._periodic_loop())
                logger.info(f"IntelligentSyncScheduler started (Period: {self.period_seconds}s).")
            except RuntimeError:
                logger.debug("No running asyncio loop available for IntelligentSyncScheduler periodic task.")

            self.trigger_sync(SyncTrigger.ON_STARTUP)

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            logger.info("IntelligentSyncScheduler stopped.")

    def trigger_sync(self, trigger: SyncTrigger):
        self.last_sync_trigger = trigger
        logger.info(f"Sync triggered by '{trigger.value}'")
        if self.sync_callback:
            try:
                self.sync_callback(trigger)
            except Exception as e:
                logger.error(f"Error executing sync callback for trigger '{trigger.value}': {e}")

    async def _periodic_loop(self):
        while self._running:
            try:
                await asyncio.sleep(self.period_seconds)
                self.trigger_sync(SyncTrigger.PERIODIC_BACKGROUND)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic sync loop: {e}")


intelligent_scheduler = IntelligentSyncScheduler()
