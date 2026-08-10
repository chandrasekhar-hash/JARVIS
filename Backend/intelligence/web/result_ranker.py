"""
Result Ranker for J.A.R.V.I.S. I2.2 V1 Web Search Foundation.
Provides intent-aware authority ranking, exact term relevance matching, and freshness prioritization.
"""
import re
from typing import List
from intelligence.web.models import SearchResultItem, WebSearchIntent, FreshnessStatus


class WebResultRanker:
    """
    Computes deterministic internal relevance scores for search results based on query terms,
    intent-aware domain authority, publication freshness, and source completeness.
    """

    def __init__(self):
        # Intent-aware official domain authority mappings
        self._intent_domain_maps = {
            "fastapi": ["fastapi.tiangolo.com"],
            "react": ["react.dev", "legacy.reactjs.org", "reactjs.org"],
            "python": ["python.org", "docs.python.org", "pypi.org"],
            "django": ["djangoproject.com", "docs.djangoproject.com"],
            "gemini": ["ai.google.dev", "deepmind.google", "blog.google"],
            "pydantic": ["docs.pydantic.dev", "pydantic.dev"],
            "fastapi_auth": ["fastapi.tiangolo.com"],
        }

    def rank_results(
        self,
        results: List[SearchResultItem],
        query: str,
        intent: WebSearchIntent,
        freshness_required: bool = False
    ) -> List[SearchResultItem]:
        """
        Ranks results in-place and returns sorted list.
        """
        if not results:
            return []

        q_terms = [t.lower() for t in re.findall(r"\b\w{3,}\b", query.lower()) if t.lower() not in {"what", "is", "the", "for", "and", "how", "find", "get", "show"}]

        for item in results:
            score = 10.0  # Base starting score

            title_lower = item.title.lower()
            snippet_lower = item.snippet.lower()
            domain_lower = item.domain.lower()

            # 1. Term relevance matching
            for term in q_terms:
                if term in title_lower:
                    score += 3.0
                if term in snippet_lower:
                    score += 1.5
                if term in domain_lower:
                    score += 2.0

            # 2. Intent-aware source authority matching
            for key, official_domains in self._intent_domain_maps.items():
                if key in query.lower() or key in title_lower:
                    if any(od in domain_lower for od in official_domains):
                        score += 5.0
                        item.is_official_source = True

            # General Intent matching
            if intent in (WebSearchIntent.DOCUMENTATION, WebSearchIntent.OFFICIAL_SOURCE):
                if item.source_type in ("documentation", "official") or item.is_official_source:
                    score += 4.0
            elif intent == WebSearchIntent.ACADEMIC:
                if item.source_type == "academic":
                    score += 4.0
            elif intent == WebSearchIntent.NEWS:
                if item.source_type == "news":
                    score += 3.0

            # Government domain intent check
            if any(k in query.lower() for k in ["gov", "government", "census", "tax", "passport"]):
                if domain_lower.endswith(".gov") or domain_lower.endswith(".gov.in") or domain_lower.endswith(".gov.uk"):
                    score += 5.0
                    item.is_official_source = True

            # 3. Freshness ranking
            if freshness_required or intent in (WebSearchIntent.CURRENT_INFORMATION, WebSearchIntent.NEWS):
                if item.freshness_status == FreshnessStatus.KNOWN_CURRENT:
                    score += 3.0
                elif item.freshness_status == FreshnessStatus.KNOWN_OLD:
                    score -= 1.5
                # UNKNOWN publication date gets 0 freshness boost (not penalized, but not boosted)

                if any(year in title_lower or year in snippet_lower for year in ["2026", "2025"]):
                    score += 2.0

            # 4. Provider rank penalty (slight decay for lower ranks)
            score -= (item.provider_rank - 1) * 0.2

            item.relevance_score = round(score, 2)

        # Sort descending by relevance_score
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results


# Global singleton instance
result_ranker = WebResultRanker()
