"""
J.A.R.V.I.S. Intelligence I2.2 V8 — Change Significance Evaluator.
Assigns explainable categorical significance (CRITICAL, HIGH, MEDIUM, LOW, COSMETIC) to detected changes.
No arbitrary numeric confidence scores.
"""
import logging
from typing import List, Tuple
from intelligence.web.monitoring.models import (
    ChangeEvidence,
    ChangeType,
    ChangeSignificance,
)

logger = logging.getLogger("JARVIS_ChangeSignificance")

CRITICAL_KEYWORDS = {"vulnerability", "cve", "security advisory", "shutdown", "deprecated", "breaking change"}
HIGH_KEYWORDS = {"release", "pricing", "price", "major", "stable", "license", "terms"}


class ChangeSignificanceEvaluator:
    """
    Evaluates categorical significance with human-readable explanations.
    """

    def evaluate_significance(self, evidences: List[ChangeEvidence]) -> Tuple[ChangeSignificance, List[str]]:
        reasons: List[str] = []
        if not evidences:
            return ChangeSignificance.COSMETIC, ["No evidence of change."]

        max_sig = ChangeSignificance.COSMETIC

        for ev in evidences:
            if not ev.is_meaningful or ev.change_type == ChangeType.COSMETIC_ONLY:
                reasons.append(f"Field '{ev.field_name}': Cosmetic change only.")
                continue

            text_sample = f"{ev.field_name} {ev.old_value} {ev.new_value}".lower()

            # Check Critical
            if any(k in text_sample for k in CRITICAL_KEYWORDS):
                max_sig = ChangeSignificance.CRITICAL
                reasons.append(f"Field '{ev.field_name}': Critical security/advisory/breaking change detected.")
                continue

            # Check High
            if ev.change_type in (ChangeType.VERSION_CHANGED, ChangeType.PRICE_CHANGED) or any(k in text_sample for k in HIGH_KEYWORDS):
                if max_sig not in (ChangeSignificance.CRITICAL,):
                    max_sig = ChangeSignificance.HIGH
                reasons.append(f"Field '{ev.field_name}': High-impact version/pricing/status update detected ({ev.old_value} -> {ev.new_value}).")
                continue

            # Check Medium
            if ev.change_type in (ChangeType.CONTENT_ADDED, ChangeType.CONTENT_REMOVED, ChangeType.VALUE_CHANGED, ChangeType.STATUS_CHANGED):
                if max_sig in (ChangeSignificance.LOW, ChangeSignificance.COSMETIC):
                    max_sig = ChangeSignificance.MEDIUM
                reasons.append(f"Field '{ev.field_name}': Meaningful content or value modification detected.")
                continue

            # Low
            if max_sig == ChangeSignificance.COSMETIC:
                max_sig = ChangeSignificance.LOW
            reasons.append(f"Field '{ev.field_name}': Minor structural or wording modification.")

        return max_sig, reasons


change_significance_evaluator = ChangeSignificanceEvaluator()
