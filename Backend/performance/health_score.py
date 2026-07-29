"""
Health Scorer Engine for J.A.R.V.I.S. Phase V1.7.
Computes quantitative health percentage scores (0% to 100%) across subsystems.
"""
from typing import Dict, Any


class HealthScorer:
    """Computes subsystem and overall system health percentage scores."""

    SUBSYSTEMS = ["WakeWord", "Audio", "Speech", "Conversation", "Voice"]

    def __init__(self):
        self._scores: Dict[str, float] = {sub: 100.0 for sub in self.SUBSYSTEMS}

    def record_score(self, subsystem: str, score: float) -> None:
        if subsystem in self.SUBSYSTEMS:
            self._scores[subsystem] = max(0.0, min(score, 100.0))

    def get_subsystem_score(self, subsystem: str) -> float:
        return self._scores.get(subsystem, 100.0)

    def get_overall_score(self) -> float:
        if not self._scores:
            return 100.0
        return round(sum(self._scores.values()) / len(self._scores), 2)

    def get_health_breakdown(self) -> Dict[str, Any]:
        overall = self.get_overall_score()
        return {
            "overall_score_percent": overall,
            "subsystems": {sub: round(score, 2) for sub, score in self._scores.items()},
            "status": "EXCELLENT" if overall >= 90 else ("GOOD" if overall >= 75 else "DEGRADED"),
        }
