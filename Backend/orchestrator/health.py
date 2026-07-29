"""
Subsystem Health Monitor for J.A.R.V.I.S. Phase V1.6 Voice Orchestrator.
Tracks availability, error counts, last activity, uptime, and restart statistics across subsystems.
"""
import time
from typing import Dict, Any
from .interfaces import IHealthMonitor


class HealthMonitor(IHealthMonitor):
    """
    Subsystem Health Monitor tracking availability of Wake Word, Audio, Speech, Conversation, Voice, and EventBus.
    """

    SUBSYSTEMS = ["WakeWord", "Audio", "Speech", "Conversation", "Voice", "EventBus"]

    def __init__(self):
        self._start_time: float = time.time()
        self._restart_count: int = 0
        self._last_error: Dict[str, str] = {}
        self._last_activity: Dict[str, float] = {sub: time.time() for sub in self.SUBSYSTEMS}
        self._healthy_state: Dict[str, bool] = {sub: True for sub in self.SUBSYSTEMS}

    def record_activity(self, subsystem: str) -> None:
        if subsystem in self.SUBSYSTEMS:
            self._last_activity[subsystem] = time.time()
            self._healthy_state[subsystem] = True

    def record_error(self, subsystem: str, error_message: str) -> None:
        if subsystem in self.SUBSYSTEMS:
            self._last_error[subsystem] = error_message
            self._healthy_state[subsystem] = False

    def is_healthy(self) -> bool:
        return all(self._healthy_state.values())

    def uptime(self) -> float:
        return time.time() - self._start_time

    def restart_count(self) -> int:
        return self._restart_count

    def increment_restart(self) -> None:
        self._restart_count += 1

    def get_status(self) -> Dict[str, Any]:
        return {
            "overall_healthy": self.is_healthy(),
            "uptime_seconds": round(self.uptime(), 2),
            "restart_count": self._restart_count,
            "subsystems": {
                sub: {
                    "healthy": self._healthy_state.get(sub, True),
                    "last_activity_sec_ago": round(time.time() - self._last_activity.get(sub, time.time()), 2),
                    "last_error": self._last_error.get(sub, None),
                }
                for sub in self.SUBSYSTEMS
            },
        }
