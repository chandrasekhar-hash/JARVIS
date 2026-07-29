"""
SLA Performance Budget Tracker for J.A.R.V.I.S. Phase V1.7.
Enforces latency targets per subsystem and detects budget breaches.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any
from .config import PerformanceConfig, performance_config


@dataclass
class BudgetStatus:
    subsystem: str
    budget_ms: float
    actual_ms: float
    breached: bool
    margin_ms: float


class PerformanceBudget:
    """Performance Budget tracker monitoring latency SLA compliance across subsystems."""

    def __init__(self, config: PerformanceConfig = performance_config):
        self.config = config
        self.budgets: Dict[str, float] = {
            "WakeWord": self.config.wake_word_budget_ms,
            "Audio": self.config.audio_budget_ms,
            "Speech": self.config.speech_recognition_budget_ms,
            "Conversation": self.config.conversation_budget_ms,
            "TTS": self.config.tts_start_budget_ms,
            "EventRouting": self.config.event_routing_budget_ms,
        }
        self._breach_counts: Dict[str, int] = {sub: 0 for sub in self.budgets}

    def check_budget(self, subsystem: str, actual_ms: float) -> BudgetStatus:
        budget_ms = self.budgets.get(subsystem, 500.0)
        breached = actual_ms > budget_ms
        if breached:
            self._breach_counts[subsystem] = self._breach_counts.get(subsystem, 0) + 1

        return BudgetStatus(
            subsystem=subsystem,
            budget_ms=budget_ms,
            actual_ms=actual_ms,
            breached=breached,
            margin_ms=round(budget_ms - actual_ms, 2),
        )

    def get_summary(self) -> Dict[str, Any]:
        return {
            "budgets_ms": self.budgets,
            "breach_counts": self._breach_counts,
            "total_breaches": sum(self._breach_counts.values()),
        }
