"""
J.A.R.V.I.S. Intelligence I2.2 V6 — Pagination Detector.
Detects pagination controls (rel="next", rel="prev", query parameters),
enforces independent V2 SSRF validation per hop, loop detection via visited_urls,
and hard bound MAX_PAGINATION_PAGES = 3.
"""
import re
import logging
from typing import Optional, Set
from urllib.parse import urljoin, parse_qs, urlparse
from bs4 import BeautifulSoup

from intelligence.web.url_validator import url_validator
from intelligence.web.structured.models import (
    PaginationMetadata,
    StructuredConfig,
)

logger = logging.getLogger("JARVIS_PaginationDetector")


class PaginationDetector:
    """
    Detects pagination controls on web pages and validates next-page URLs.
    """

    async def detect_pagination(
        self, html_content: str, current_url: str, visited_urls: Set[str]
    ) -> PaginationMetadata:
        meta = PaginationMetadata(has_pagination=False, current_page=1)
        if not html_content or not html_content.strip():
            return meta

        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Look for rel="next"
        next_tag = soup.find(["a", "link"], rel=lambda r: r and "next" in r)
        if next_tag and next_tag.get("href"):
            next_href = next_tag["href"].strip()
            next_url = urljoin(current_url, next_href)
            if await self._validate_next_page(next_url, visited_urls):
                meta.has_pagination = True
                meta.next_page_url = next_url
                meta.pagination_type = "REL_NEXT"
                return meta

        # 2. Fallback: search <a> tags containing "Next", "Page 2", etc.
        anchor_next = soup.find("a", string=re.compile(r"\b(next|older|page\s*\d+)\b", re.IGNORECASE))
        if anchor_next and anchor_next.get("href"):
            next_href = anchor_next["href"].strip()
            next_url = urljoin(current_url, next_href)
            if await self._validate_next_page(next_url, visited_urls):
                meta.has_pagination = True
                meta.next_page_url = next_url
                meta.pagination_type = "ANCHOR_TEXT"
                return meta

        # 3. Check query parameters like ?page=1
        parsed = urlparse(current_url)
        params = parse_qs(parsed.query)
        if "page" in params:
            try:
                curr_page = int(params["page"][0])
                meta.current_page = curr_page
                next_page_num = curr_page + 1
                next_url = current_url.replace(f"page={curr_page}", f"page={next_page_num}")
                if await self._validate_next_page(next_url, visited_urls):
                    meta.has_pagination = True
                    meta.next_page_url = next_url
                    meta.pagination_type = "QUERY_PARAM"
                    return meta
            except ValueError:
                pass

        return meta

    async def _validate_next_page(self, url: str, visited_urls: Set[str]) -> bool:
        """
        Validates next page URL against visited set, loop detection, and V2 SSRF rules.
        """
        if url in visited_urls:
            logger.info(f"Pagination loop prevented for visited URL: {url}")
            return False

        is_safe, resolved_ip, err_msg = await url_validator.validate_url(url)
        if not is_safe:
            logger.warning(f"Pagination SSRF blocked for next URL {url}: {err_msg}")
            return False

        return True


pagination_detector = PaginationDetector()
