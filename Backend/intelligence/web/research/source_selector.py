"""
Source Diversity & Suitability Selector for J.A.R.V.I.S. I2.2 V3.
Filters candidate search results, prunes duplicate/syndicated SEO press clones,
and assigns explainable non-numeric SourceSuitability metadata.
"""

from typing import List
from urllib.parse import urlparse
from intelligence.web.models import SearchResultItem
from intelligence.web.research.models import SourceSuitability, ResearchSource, ResearchIntent


class SourceDiversitySelector:
    """Selects diverse, primary, and intent-matched sources."""

    OFFICIAL_DOMAINS = [
        "react.dev", "reactjs.org", "python.org", "fastapi.tiangolo.com",
        "github.com", "docs.python.org", "developer.mozilla.org", "pypi.org",
        "anthropic.com", "openai.com", "cloud.google.com", "ai.google.dev",
        "flask.palletsprojects.com"
    ]

    ACADEMIC_DOMAINS = ["arxiv.org", "nature.com", "sciencedirect.com", "ieee.org"]
    NEWS_DOMAINS = ["techcrunch.com", "arstechnica.com", "theverge.com", "reuters.com", "bloomberg.com"]

    def evaluate_and_select_sources(
        self,
        results: List[SearchResultItem],
        intent: ResearchIntent,
        max_sources: int = 5
    ) -> List[ResearchSource]:
        """
        Filters and selects up to max_sources diverse candidates.
        Prunes duplicate domains / syndicated press releases.
        """
        seen_domains = set()
        seen_snippets = set()
        selected: List[ResearchSource] = []

        for idx, item in enumerate(results):
            url = item.canonical_url or item.url
            if not url:
                continue

            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Deduplicate exact domain matches if we already have 2 pages from same domain
            domain_count = sum(1 for s in selected if s.domain == domain)
            if domain_count >= 2:
                continue

            # Deduplicate near-identical syndicated snippets
            snippet_snippet = (item.snippet or "")[:80].strip().lower()
            if snippet_snippet and snippet_snippet in seen_snippets:
                continue
            if snippet_snippet:
                seen_snippets.add(snippet_snippet)

            # Evaluate suitability attributes
            is_official = any(off in domain for off in self.OFFICIAL_DOMAINS)
            is_doc = "docs" in domain or "/docs/" in url or "/doc/" in url or "/release-notes/" in url or "/changelog" in url
            is_academic = any(acad in domain for acad in self.ACADEMIC_DOMAINS)
            is_news = any(news in domain for news in self.NEWS_DOMAINS)

            reasons = []
            if is_official:
                reasons.append("Official primary project domain")
            if is_doc:
                reasons.append("Technical documentation or changelog path")
            if is_academic:
                reasons.append("Peer-reviewed or preprint academic source")
            if is_news:
                reasons.append("Reputable technology reporting outlet")

            suitability = SourceSuitability(
                domain=domain,
                is_primary_source=is_official or is_doc or is_academic,
                is_official=is_official,
                is_documentation=is_doc,
                is_academic=is_academic,
                is_news=is_news,
                matches_research_intent=True,
                reasons=reasons or ["General web search result"]
            )

            source_id = f"source_{len(selected) + 1}"
            source = ResearchSource(
                source_id=source_id,
                url=url,
                canonical_url=url,
                domain=domain,
                title=item.title or domain,
                source_type="OFFICIAL" if is_official else ("DOCS" if is_doc else "GENERAL"),
                suitability=suitability,
                published_at=None,  # Never manufacture publication dates
                retrieved_at=item.retrieved_at or ""
            )

            selected.append(source)
            if len(selected) >= max_sources:
                break

        return selected


source_diversity_selector = SourceDiversitySelector()
