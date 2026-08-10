"""
Link Analyzer Engine for J.A.R.V.I.S. I2.2 V5.
Extracts and classifies candidate webpage links from legitimately retrieved V2 pages.
Enforces explicit safety, eligibility, and rejection reason states.
Anchor text is strictly untrusted content with zero instructional authority.
"""

import re
from typing import List, Set, Tuple
from urllib.parse import urljoin, urlparse

from intelligence.web.url_validator import url_validator
from intelligence.web.deep_research.models import (
    DiscoveredLink,
    LinkCategory,
    LinkRejectionReason
)


class LinkAnalyzer:
    """Extracts, validates, and classifies candidate links from retrieved pages."""

    OFFICIAL_PATTERNS = ["docs.", "blog.", "github.com", "/releases", "/changelog", "/docs/", "peps.python.org", ".gov"]
    PRIMARY_PATTERNS = ["github.com", "gitlab.com", "bitbucket.org", "arxiv.org", "pypi.org", "npmjs.com"]
    ACADEMIC_PATTERNS = ["arxiv.org", "acm.org", "ieee.org", "nature.com", "sciencedirect.com", "researchgate.net"]
    NEWS_PATTERNS = ["techcrunch.com", "news.ycombinator.com", "reuters.com", "bloomberg.com", "arstechnica.com", "theverge.com"]

    async def extract_and_classify_links(
        self,
        html_content: str,
        source_url: str,
        visited_urls: Set[str],
        max_links: int = 10
    ) -> List[DiscoveredLink]:
        """
        Extracts links from HTML, evaluates safety via V2 UrlSafetyValidator,
        and assigns explicit eligibility and rejection reasons.
        """
        discovered: List[DiscoveredLink] = []
        if not html_content or not source_url:
            return discovered

        # Extract anchor tags via regex (clean, fast, no extra dependency)
        anchor_matches = re.findall(
            r'<a\s+(?:[^>]*?\s+)?href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            html_content,
            re.IGNORECASE | re.DOTALL
        )

        for raw_href, raw_text in anchor_matches:
            if len(discovered) >= max_links:
                break

            href = raw_href.strip()
            # Clean anchor text
            clean_text = re.sub(r'<[^>]+>', '', raw_text).strip()[:100]

            # Resolve relative URLs safely
            try:
                abs_url = urljoin(source_url, href)
            except Exception:
                continue

            parsed = urlparse(abs_url)
            if parsed.scheme not in ("http", "https"):
                # Non-HTTP scheme
                d_link = DiscoveredLink(
                    url=abs_url,
                    canonical_url=abs_url,
                    anchor_text=clean_text or abs_url,
                    source_page_url=source_url,
                    category=LinkCategory.UNSAFE,
                    is_url_safe=False,
                    is_eligible_for_selection=False,
                    rejection_reason=LinkRejectionReason.NON_HTTP_SCHEME
                )
                discovered.append(d_link)
                continue

            # Validate URL with V2 UrlSafetyValidator
            is_safe, resolved_ip, reason = await url_validator.validate_url(abs_url)
            if not is_safe:
                rej_reason = LinkRejectionReason.SSRF_BLOCKED
                if "IP" in reason or "encoded" in reason:
                    rej_reason = LinkRejectionReason.IP_ENCODED
                elif "private" in reason or "loopback" in reason or "local" in reason:
                    rej_reason = LinkRejectionReason.LOOPBACK_OR_PRIVATE

                d_link = DiscoveredLink(
                    url=abs_url,
                    canonical_url=abs_url,
                    anchor_text=clean_text or abs_url,
                    source_page_url=source_url,
                    category=LinkCategory.UNSAFE,
                    is_url_safe=False,
                    is_eligible_for_selection=False,
                    rejection_reason=rej_reason
                )
                discovered.append(d_link)
                continue

            canonical = abs_url

            # Check visited deduplication
            if abs_url in visited_urls or canonical in visited_urls:
                d_link = DiscoveredLink(
                    url=abs_url,
                    canonical_url=canonical,
                    anchor_text=clean_text or abs_url,
                    source_page_url=source_url,
                    category=LinkCategory.RELATED,
                    is_url_safe=True,
                    is_eligible_for_selection=False,
                    rejection_reason=LinkRejectionReason.ALREADY_VISITED
                )
                discovered.append(d_link)
                continue

            # Classify Link Category
            cat = self._classify_category(canonical, clean_text)

            d_link = DiscoveredLink(
                url=abs_url,
                canonical_url=canonical,
                anchor_text=clean_text or abs_url,
                source_page_url=source_url,
                category=cat,
                is_url_safe=True,
                is_eligible_for_selection=True,
                rejection_reason=LinkRejectionReason.NONE
            )
            discovered.append(d_link)

        return discovered

    def _classify_category(self, url: str, anchor_text: str) -> LinkCategory:
        """Classifies link category based on URL structure and domain."""
        url_lower = url.lower()
        text_lower = anchor_text.lower()

        if any(p in url_lower for p in self.ACADEMIC_PATTERNS):
            return LinkCategory.ACADEMIC

        if any(p in url_lower for p in self.PRIMARY_PATTERNS):
            return LinkCategory.PRIMARY_SOURCE

        if any(p in url_lower for p in self.OFFICIAL_PATTERNS) or "official" in text_lower or "documentation" in text_lower:
            return LinkCategory.OFFICIAL

        if any(p in url_lower for p in self.NEWS_PATTERNS):
            return LinkCategory.NEWS

        if "docs" in url_lower or "guide" in url_lower or "api" in url_lower:
            return LinkCategory.DOCUMENTATION

        return LinkCategory.RELATED


link_analyzer = LinkAnalyzer()
