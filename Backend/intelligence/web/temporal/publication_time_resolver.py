"""
Publication Time Resolver for J.A.R.V.I.S. I2.2 V4.
Extracts published_at, updated_at, event_time, time_source, and time_precision.
Enforces strict integrity: published_at=None when missing; zero timestamp manufacturing.
"""

import re
from typing import Optional, Tuple
from intelligence.web.temporal.models import (
    TemporalMetadata,
    TimeSource,
    TimePrecision,
    FreshnessCategory
)


class PublicationTimeResolver:
    """Extracts publication and event timestamps with explicit provenance and precision."""

    DATE_PATTERNS = [
        (r"\b(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)\b", TimePrecision.EXACT_DATETIME),
        (r"\b(\d{4}-\d{2}-\d{2})\b", TimePrecision.DATE_ONLY),
        (r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b", TimePrecision.DATE_ONLY),
        (r"\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b", TimePrecision.DATE_ONLY)
    ]

    def resolve_publication_time(
        self,
        html_text: str,
        retrieved_at: str,
        meta_dict: Optional[dict] = None
    ) -> TemporalMetadata:
        """
        Extracts temporal metadata from HTML or structured headers.
        If publication time is unavailable, published_at remains None.
        retrieved_at is NEVER substituted for published_at.
        """
        meta_dict = meta_dict or {}

        published_at: Optional[str] = None
        updated_at: Optional[str] = None
        time_source = TimeSource.UNKNOWN
        time_precision = TimePrecision.UNKNOWN

        # 1. Structured Metadata / JSON-LD / OpenGraph
        if "article:published_time" in meta_dict:
            published_at = meta_dict["article:published_time"]
            time_source = TimeSource.OPEN_GRAPH
            time_precision = TimePrecision.EXACT_DATETIME
        elif "datePublished" in meta_dict:
            published_at = meta_dict["datePublished"]
            time_source = TimeSource.JSON_LD
            time_precision = TimePrecision.EXACT_DATETIME

        if "article:modified_time" in meta_dict:
            updated_at = meta_dict["article:modified_time"]
        elif "dateModified" in meta_dict:
            updated_at = meta_dict["dateModified"]

        # 2. HTML <time> tags or regex fallback in text if structured meta missing
        if published_at is None:
            time_match = re.search(r'<time[^>]*datetime=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
            if time_match:
                published_at = time_match.group(1).strip()
                time_source = TimeSource.HTML_TIME_ELEMENT
                time_precision = TimePrecision.EXACT_DATETIME if "T" in published_at else TimePrecision.DATE_ONLY

        if published_at is None:
            for pat, prec in self.DATE_PATTERNS:
                m = re.search(pat, html_text, re.IGNORECASE)
                if m:
                    published_at = m.group(0).strip()
                    time_source = TimeSource.ARTICLE_TEXT
                    time_precision = prec
                    break

        return TemporalMetadata(
            published_at=published_at,  # Retains None if not found
            updated_at=updated_at,
            event_time=published_at,
            retrieved_at=retrieved_at,
            time_source=time_source,
            time_precision=time_precision,
            freshness=FreshnessCategory.UNKNOWN
        )


publication_time_resolver = PublicationTimeResolver()
