"""
J.A.R.V.I.S. Intelligence I2.2 V8 — Semantic Change Detector.
Distinguishes MEANINGFUL_CHANGE from COSMETIC_ONLY changes conservatively.
Never strips numeric version, price, or date facts as noise.
"""
import re
import logging
from typing import List
from intelligence.web.monitoring.models import ChangeEvidence, ChangeType

logger = logging.getLogger("JARVIS_SemanticChangeDetector")


class SemanticChangeDetector:
    """
    Evaluates evidence items to categorize meaningful vs cosmetic changes.
    """

    def analyze_evidences(self, evidences: List[ChangeEvidence]) -> List[ChangeEvidence]:
        analyzed: List[ChangeEvidence] = []
        for ev in evidences:
            old_str = (ev.old_value or "").strip()
            new_str = (ev.new_value or "").strip()

            # 1. Identical normalized string check
            if old_str == new_str:
                ev.is_meaningful = False
                ev.change_type = ChangeType.COSMETIC_ONLY
                analyzed.append(ev)
                continue

            # 2. Whitespace / Formatting only check
            if re.sub(r"\s+", "", old_str) == re.sub(r"\s+", "", new_str):
                ev.is_meaningful = False
                ev.change_type = ChangeType.COSMETIC_ONLY
                analyzed.append(ev)
                continue

            # 3. Numeric / Price / Version / Date / Status check -> ALWAYS MEANINGFUL
            has_digits = any(c.isdigit() for c in old_str + new_str)
            if ev.change_type in (
                ChangeType.VERSION_CHANGED,
                ChangeType.PRICE_CHANGED,
                ChangeType.STATUS_CHANGED,
                ChangeType.DATE_CHANGED,
                ChangeType.VALUE_CHANGED,
            ) or has_digits:
                ev.is_meaningful = True
                analyzed.append(ev)
                continue

            # Default: meaningful text structural change
            ev.is_meaningful = True
            analyzed.append(ev)

        return analyzed


semantic_change_detector = SemanticChangeDetector()
