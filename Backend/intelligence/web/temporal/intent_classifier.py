"""
Temporal Intent Classifier for J.A.R.V.I.S. I2.2 V4.
Evaluates query to determine temporal intent category.
"""

import re
from typing import Tuple
from intelligence.web.temporal.models import TemporalIntent


class TemporalIntentClassifier:
    """Classifies temporal intent and applies fast-bypass logic."""

    TODAY_PATTERNS = [r"\btoday\b", r"\btoday's\b"]
    YESTERDAY_PATTERNS = [r"\byesterday\b", r"\byesterday's\b"]
    LAST_24_HOURS_PATTERNS = [r"\blast 24 hours\b", r"\bpast 24 hours\b", r"\b24h\b"]
    THIS_WEEK_PATTERNS = [r"\bthis week\b", r"\bpast week\b", r"\blast 7 days\b"]
    THIS_MONTH_PATTERNS = [r"\bthis month\b", r"\bpast month\b", r"\blast 30 days\b"]
    SINCE_LAST_CHECK_PATTERNS = [r"\bsince i last asked\b", r"\banything new\b", r"\bwhat changed since\b", r"\bhas anything changed\b"]
    BREAKING_NEWS_PATTERNS = [r"\bbreaking news\b", r"\bjust in\b", r"\burgent update\b"]
    TIMELINE_PATTERNS = [r"\btimeline\b", r"\bchronology\b", r"\bsequence of events\b", r"\bhistory of updates\b"]
    LATEST_PATTERNS = [r"\blatest\b", r"\brecent\b", r"\bnewest\b", r"\bwhat's new\b", r"\bupdates\b"]

    BYPASS_NON_TEMPORAL = [
        r"^what is recursion\??$",
        r"^explain binary search\??$",
        r"^define \w+\??$",
        r"^how does a hash table work\??$"
    ]

    def classify_intent(self, query: str) -> Tuple[TemporalIntent, bool]:
        """
        Classifies query into a TemporalIntent.
        Returns (TemporalIntent, is_temporal).
        """
        q_clean = query.strip().lower()

        # 1. Fast Bypass: Non-temporal conceptual query
        for pat in self.BYPASS_NON_TEMPORAL:
            if re.search(pat, q_clean):
                return TemporalIntent.NON_TEMPORAL, False

        # 2. Match Temporal Patterns
        for pat in self.SINCE_LAST_CHECK_PATTERNS:
            if re.search(pat, q_clean):
                return TemporalIntent.SINCE_LAST_CHECK, True

        for pat in self.TODAY_PATTERNS:
            if re.search(pat, q_clean):
                return TemporalIntent.TODAY, True

        for pat in self.YESTERDAY_PATTERNS:
            if re.search(pat, q_clean):
                return TemporalIntent.YESTERDAY, True

        for pat in self.LAST_24_HOURS_PATTERNS:
            if re.search(pat, q_clean):
                return TemporalIntent.LAST_24_HOURS, True

        for pat in self.THIS_WEEK_PATTERNS:
            if re.search(pat, q_clean):
                return TemporalIntent.THIS_WEEK, True

        for pat in self.THIS_MONTH_PATTERNS:
            if re.search(pat, q_clean):
                return TemporalIntent.THIS_MONTH, True

        for pat in self.BREAKING_NEWS_PATTERNS:
            if re.search(pat, q_clean):
                return TemporalIntent.BREAKING_NEWS, True

        for pat in self.TIMELINE_PATTERNS:
            if re.search(pat, q_clean):
                return TemporalIntent.EVENT_TIMELINE, True

        for pat in self.LATEST_PATTERNS:
            if re.search(pat, q_clean):
                return TemporalIntent.LATEST, True

        if "since" in q_clean or "after" in q_clean:
            return TemporalIntent.SINCE_DATE, True

        # Default: non-temporal
        return TemporalIntent.NON_TEMPORAL, False


temporal_intent_classifier = TemporalIntentClassifier()
