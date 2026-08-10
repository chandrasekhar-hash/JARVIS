"""
Primary Announcement Resolver for J.A.R.V.I.S. I2.2 V4.
Identifies official primary announcements, links secondary reports to primary sources,
and distinguishes primary sources from independent secondary confirmations.
"""

from typing import List, Tuple, Optional
from intelligence.web.research.models import ResearchSource, SourceSuitability


class PrimaryAnnouncementResolver:
    """Resolves primary announcements behind news stories."""

    PRIMARY_URL_PATTERNS = [
        "/release-notes", "/releases/tag/", "/blog/", "/announcements/",
        "/peps/pep-", "/advisories/", "/changelog", "docs."
    ]

    def resolve_primary_announcements(
        self,
        sources: List[ResearchSource]
    ) -> Tuple[Optional[ResearchSource], List[ResearchSource]]:
        """
        Identifies the primary official announcement source (if available)
        and separates it from independent secondary reporting sources.
        Does NOT automatically assume primary source is 100% complete/correct; preserves contradictions.
        """
        primary_source: Optional[ResearchSource] = None
        secondary_sources: List[ResearchSource] = []

        for src in sources:
            url_lower = src.canonical_url.lower()
            is_primary_path = any(p in url_lower for p in self.PRIMARY_URL_PATTERNS)

            if (src.suitability.is_official or src.suitability.is_primary_source or is_primary_path) and primary_source is None:
                primary_source = src
            else:
                secondary_sources.append(src)

        return primary_source, secondary_sources


primary_announcement_resolver = PrimaryAnnouncementResolver()
