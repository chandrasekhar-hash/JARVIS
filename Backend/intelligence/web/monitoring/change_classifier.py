"""
J.A.R.V.I.S. Intelligence I2.2 V8 — Change Classifier.
Classifies detected diffs into explicit ChangeType enums.
"""
import logging
from typing import List
from intelligence.web.monitoring.models import ChangeEvidence, ChangeType

logger = logging.getLogger("JARVIS_ChangeClassifier")


class ChangeClassifier:
    """
    Classifies ChangeEvidence objects based on field semantics and text diff patterns.
    """

    def classify_change(self, ev: ChangeEvidence) -> ChangeType:
        if not ev.is_meaningful:
            return ChangeType.COSMETIC_ONLY

        field_name = (ev.field_name or "").lower()
        if "version" in field_name or "release" in field_name:
            return ChangeType.VERSION_CHANGED
        if "price" in field_name or "cost" in field_name:
            return ChangeType.PRICE_CHANGED
        if "status" in field_name or "availability" in field_name:
            return ChangeType.STATUS_CHANGED
        if "date" in field_name:
            return ChangeType.DATE_CHANGED

        return ev.change_type


change_classifier = ChangeClassifier()
