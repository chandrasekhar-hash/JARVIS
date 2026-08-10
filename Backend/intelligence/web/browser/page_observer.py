"""
J.A.R.V.I.S. Intelligence I2.2 V7 — Page Observer.
Generates structured BrowserPageObservation summarizing visible content, headings, interactive element references,
tables, and page state fingerprints under strict memory bounds.
"""
import hashlib
import logging
import time
from typing import Dict, Any, List
from bs4 import BeautifulSoup

from intelligence.web.browser.models import (
    BrowserPageObservation,
    BrowserConfig,
)
from intelligence.web.browser.element_selector import element_selector

logger = logging.getLogger("JARVIS_PageObserver")


class PageObserver:
    """
    Parses DOM content into structured observations without loading megabytes of HTML into LLM context.
    """

    def observe_page(
        self, html_content: str, canonical_url: str, title: str = ""
    ) -> BrowserPageObservation:
        if not html_content or not html_content.strip():
            obs_id = f"obs_{int(time.time() * 1000)}"
            return BrowserPageObservation(
                observation_id=obs_id,
                canonical_url=canonical_url,
                title=title,
                visible_text="",
                content_fingerprint="empty",
            )

        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Extract Page Title
        if not title:
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else "Untitled Page"

        # 2. Extract Visible Text under MAX_VISIBLE_TEXT_CHARS bound
        visible_text = soup.get_text(" ", strip=True)
        if len(visible_text) > BrowserConfig.MAX_VISIBLE_TEXT_CHARS:
            visible_text = visible_text[: BrowserConfig.MAX_VISIBLE_TEXT_CHARS] + "...[TRUNCATED]"

        # 3. Compute Page State Fingerprint
        fingerprint_src = f"{canonical_url}|{title}|{visible_text[:1000]}"
        content_fingerprint = hashlib.md5(fingerprint_src.encode("utf-8")).hexdigest()
        obs_id = f"obs_{content_fingerprint[:10]}"

        # 4. Extract Headings under MAX_HEADINGS bound
        headings: List[str] = []
        for h in soup.find_all(["h1", "h2", "h3"], limit=BrowserConfig.MAX_HEADINGS):
            text = h.get_text(strip=True)
            if text:
                headings.append(text)

        # 5. Parse Interactive Elements via ElementSelector
        interactive_elements = element_selector.parse_and_index_elements(
            html_content, obs_id, content_fingerprint
        )

        return BrowserPageObservation(
            observation_id=obs_id,
            canonical_url=canonical_url,
            title=title,
            visible_text=visible_text,
            headings=headings,
            interactive_elements=interactive_elements,
            page_timestamp=time.time(),
            network_idle_status=True,
            content_fingerprint=content_fingerprint,
        )


page_observer = PageObserver()
