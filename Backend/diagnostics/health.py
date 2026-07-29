"""
System Health Diagnostic Checker for J.A.R.V.I.S. Phase V1.8.
Inspects Speech, Conversation, Voice, Audio, Orchestrator, Performance, Memory, CPU, Queues, Caches.
"""
import time
import logging
from typing import Dict, Any, Optional

from .interfaces import IHealthChecker
from .models import HealthSnapshot, SubsystemStatus

logger = logging.getLogger("JARVIS_HealthChecker")


class HealthChecker(IHealthChecker):
    """
    Comprehensive System & Subsystem Health Diagnostic Evaluator.
    """

    SUBSYSTEM_NAMES = [
        "WakeWord",
        "Audio",
        "Speech",
        "Conversation",
        "Voice",
        "Orchestrator",
        "Performance",
        "Memory",
        "CPU",
        "Queues",
        "Caches",
    ]

    def __init__(self):
        self._statuses: Dict[str, SubsystemStatus] = {
            name: SubsystemStatus(subsystem_name=name, healthy=True)
            for name in self.SUBSYSTEM_NAMES
        }

    def record_subsystem_health(
        self,
        subsystem_name: str,
        healthy: bool,
        latency_ms: float = 0.0,
        error_count: int = 0,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        if subsystem_name in self._statuses:
            status = self._statuses[subsystem_name]
            status.healthy = healthy
            status.latency_ms = latency_ms
            status.error_count = error_count
            status.last_activity_sec_ago = 0.0
            if details:
                status.details.update(details)

    def check_health(self) -> HealthSnapshot:
        healthy_count = sum(1 for s in self._statuses.values() if s.healthy)
        total = len(self._statuses)
        score = round((healthy_count / total * 100.0), 2) if total > 0 else 100.0
        overall_healthy = all(s.healthy for s in self._statuses.values())

        return HealthSnapshot(
            timestamp=time.time(),
            overall_healthy=overall_healthy,
            overall_score=score,
            subsystems=dict(self._statuses),
        )
