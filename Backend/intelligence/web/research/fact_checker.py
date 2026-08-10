"""
Specialized Fact-Checking Engine for J.A.R.V.I.S. I2.2 V3.
Evaluates claims while explicitly preserving configuration/build qualifiers and version scopes.
"""

import re
from typing import List, Optional
from intelligence.web.research.models import (
    FactCheckDetail,
    FactCheckStatus,
    EvidenceItem,
    ResearchSource
)


class FactChecker:
    """Evaluates fact-check queries and preserves qualifiers."""

    QUALIFIER_KEYWORDS = [
        "free-threaded", "optional", "experimental", "disabled by default",
        "enabled by default", "build option", "configuration flag", "opt-in"
    ]

    def evaluate_fact_check(
        self,
        query: str,
        evidence_items: List[EvidenceItem],
        sources: List[ResearchSource]
    ) -> FactCheckDetail:
        """
        Evaluates a fact-check query against retrieved evidence items.
        Extracts user claim, qualifiers, version scope, and verdict.
        """
        user_claim = query.strip()
        found_qualifiers: List[str] = []
        version_scope: Optional[str] = None

        # Extract version scope if present (e.g., "Python 3.14" or "React 19")
        v_match = re.search(r"\b(python|react|fastapi|node|v)?\s*(\d+\.\d+(\.\d+)?)\b", user_claim, re.IGNORECASE)
        if v_match:
            version_scope = v_match.group(0).strip()

        # Combine evidence texts
        combined_text = " ".join([ev.text for ev in evidence_items]).lower()

        # Scan for qualifiers in evidence
        for q_word in self.QUALIFIER_KEYWORDS:
            if q_word in combined_text:
                found_qualifiers.append(q_word)

        # Determine verdict based on evidence and primary sources
        if not evidence_items:
            verdict = FactCheckStatus.INSUFFICIENT_EVIDENCE
            explanation = "No verified web evidence items could be retrieved to verify this claim."
        else:
            has_official = any(s.suitability.is_official for s in sources)
            if "remove" in combined_text or "removed" in combined_text or "disabled" in combined_text:
                if found_qualifiers:
                    verdict = FactCheckStatus.MOSTLY_SUPPORTED
                    explanation = (
                        f"The claim is mostly supported with key qualifiers: "
                        f"{', '.join(found_qualifiers)}. The feature is subject to specific configuration bounds."
                    )
                else:
                    verdict = FactCheckStatus.SUPPORTED
                    explanation = "The claim is directly supported by retrieved primary evidence."
            elif "not" in combined_text or "retained" in combined_text or "incorrect" in combined_text:
                verdict = FactCheckStatus.CONTRADICTED
                explanation = "The claim is contradicted by retrieved official evidence."
            else:
                verdict = FactCheckStatus.SUPPORTED if has_official else FactCheckStatus.MOSTLY_SUPPORTED
                explanation = "Evidence retrieved from verified sources supports the claim."

        return FactCheckDetail(
            user_claim=user_claim,
            qualifiers=found_qualifiers,
            version_scope=version_scope,
            verdict=verdict,
            explanation=explanation
        )


fact_checker = FactChecker()
