"""
Deduplicator for J.A.R.V.I.S. I2.2 V1 Web Search Foundation.
Deduplicates search results by canonical URL and text similarity without merging distinct pages.
"""
from typing import List
from intelligence.web.models import SearchResultItem


class WebResultDeduplicator:
    """
    Handles deduplication of normalized search result items.
    """

    def deduplicate(self, results: List[SearchResultItem]) -> List[SearchResultItem]:
        """
        Deduplicates search results by canonical URL and title similarity.
        Preserves original ranking order of first seen item.
        """
        if not results:
            return []

        unique_items: List[SearchResultItem] = []
        seen_canonical_urls = set()
        seen_title_prefixes = set()

        for item in results:
            c_url = item.canonical_url.lower().rstrip("/")
            if c_url in seen_canonical_urls:
                continue

            # Check title prefix (first 40 chars normalized)
            norm_title_prefix = "".join(e for e in item.title.lower() if e.isalnum())[:40]
            if norm_title_prefix and norm_title_prefix in seen_title_prefixes:
                continue

            seen_canonical_urls.add(c_url)
            if norm_title_prefix:
                seen_title_prefixes.add(norm_title_prefix)

            unique_items.append(item)

        return unique_items


# Global singleton instance
deduplicator = WebResultDeduplicator()
