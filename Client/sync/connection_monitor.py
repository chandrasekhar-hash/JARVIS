import time
import logging
from typing import Dict, Any, List, Callable, Optional

logger = logging.getLogger("JARVIS_Client_ConnectionMonitor")


class ConnectionMonitor:
    """
    ConnectionMonitor tracking client connection state, quality score, last sync time,
    and pending offline change count. Exposes state listener callbacks for UI updates.
    """

    def __init__(self):
        self.state: str = "OFFLINE"  # CONNECTED, CONNECTING, OFFLINE, SYNCHRONIZING, ERROR
        self.last_sync_timestamp: Optional[float] = None
        self.pending_changes_count: int = 0
        self.quality_score: float = 1.0  # 0.0 (poor) -> 1.0 (excellent)
        self.error_message: str = ""
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []

    def register_listener(self, callback: Callable[[Dict[str, Any]], None]):
        self._listeners.append(callback)

    def set_state(self, new_state: str, error_msg: str = ""):
        if self.state != new_state or error_msg != self.error_message:
            self.state = new_state
            self.error_message = error_msg
            logger.info(f"Connection status changed to '{self.state}' ({error_msg})")
            self._notify()

    def update_sync_success(self, pending_count: int = 0):
        self.last_sync_timestamp = time.time()
        self.pending_changes_count = pending_count
        self.state = "CONNECTED"
        self._notify()

    def update_pending_count(self, pending_count: int):
        self.pending_changes_count = pending_count
        self._notify()

    def _notify(self):
        info = self.get_status()
        for listener in self._listeners:
            try:
                listener(info)
            except Exception as e:
                logger.error(f"Error in connection monitor listener: {e}")

    def get_status(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "last_sync_timestamp": self.last_sync_timestamp,
            "pending_changes_count": self.pending_changes_count,
            "quality_score": self.quality_score,
            "error_message": self.error_message,
            "is_online": self.state in ["CONNECTED", "SYNCHRONIZING"]
        }


connection_monitor = ConnectionMonitor()
