"""
Research Intent Classifier for J.A.R.V.I.S. I2.2 V3.
Evaluates query to determine if full V3 multi-source research is needed,
or if fast-bypass to NO_WEB or SIMPLE_LOOKUP applies.
"""

import re
from typing import Tuple
from intelligence.web.research.models import ResearchIntent


class ResearchIntentClassifier:
    """Classifies research intent and applies fast-bypass logic."""

    FACT_CHECK_PATTERNS = [
        r"\bis (it )?true that\b",
        r"\bdid \w+ (remove|add|change|cancel|release)\b",
        r"\bverify (if|whether|that)\b",
        r"\bfact check\b",
        r"\bis \w+ (really|actually) (true|false|released|deprecated)\b"
    ]

    COMPARISON_PATTERNS = [
        r"\bcompare\b",
        r"\bvs\.?\b",
        r"\bdifference between\b",
        r"\bversus\b",
        r"\bpros and cons\b",
        r"\bwhich is better\b"
    ]

    TECH_PATTERNS = [
        r"\bwhat changed in\b",
        r"\brelease notes\b",
        r"\bchangelog\b",
        r"\bapi capabilities\b",
        r"\bdocumentation for\b",
        r"\bhow to use\b",
        r"\bmigration guide\b"
    ]

    NEWS_PATTERNS = [
        r"\blatest news\b",
        r"\bwhat happened today\b",
        r"\bdevelopments today\b",
        r"\brecent updates\b",
        r"\bbreaking news\b"
    ]

    BYPASS_CONCEPTUAL_PATTERNS = [
        r"^what is recursion\??$",
        r"^explain binary search\??$",
        r"^define \w+\??$",
        r"^how does a hash table work\??$"
    ]

    BYPASS_SIMPLE_LOOKUP_PATTERNS = [
        r"^latest python version\??$",
        r"^current date\??$",
        r"^react version\??$"
    ]

    def classify_intent(self, query: str) -> Tuple[ResearchIntent, bool]:
        """
        Classifies query into a ResearchIntent.
        Returns (ResearchIntent, is_full_v3_research_needed).
        """
        q_clean = query.strip().lower()

        # 1. Fast Bypass: No Web
        for pat in self.BYPASS_CONCEPTUAL_PATTERNS:
            if re.search(pat, q_clean):
                return ResearchIntent.NO_WEB, False

        # 2. Fast Bypass: Simple Lookup (V1/V2 single lookup sufficient)
        for pat in self.BYPASS_SIMPLE_LOOKUP_PATTERNS:
            if re.search(pat, q_clean):
                return ResearchIntent.SIMPLE_LOOKUP, False

        # 3. Intent Detection Rules
        for pat in self.FACT_CHECK_PATTERNS:
            if re.search(pat, q_clean):
                return ResearchIntent.FACT_CHECK, True

        for pat in self.COMPARISON_PATTERNS:
            if re.search(pat, q_clean):
                return ResearchIntent.PRODUCT_COMPARISON, True

        for pat in self.TECH_PATTERNS:
            if re.search(pat, q_clean):
                return ResearchIntent.TECHNICAL_RESEARCH, True

        for pat in self.NEWS_PATTERNS:
            if re.search(pat, q_clean):
                return ResearchIntent.NEWS_SYNTHESIS, True

        if "official" in q_clean or "docs" in q_clean:
            return ResearchIntent.OFFICIAL_DOCUMENTATION, True

        if "arxiv" in q_clean or "paper" in q_clean or "study" in q_clean:
            return ResearchIntent.ACADEMIC_RESEARCH, True

        # Default to GENERAL_RESEARCH
        return ResearchIntent.GENERAL_RESEARCH, True


research_intent_classifier = ResearchIntentClassifier()
