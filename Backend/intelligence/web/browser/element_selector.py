"""
J.A.R.V.I.S. Intelligence I2.2 V6 — Element Selector & Indexer.
Generates abstract, stable internal element references (e.g. element_1, element_2) tied to page_state_fingerprint and observation_id.
Maps DOM elements by ARIA role, accessible name, visible text, and tag type safely.
"""
import hashlib
import logging
from typing import List, Dict, Any, Tuple
from bs4 import BeautifulSoup, Tag

from intelligence.web.browser.models import ElementRef, BrowserConfig

logger = logging.getLogger("JARVIS_ElementSelector")


class ElementSelector:
    """
    Scans DOM HTML content to identify and index interactive elements into stable references.
    """

    def parse_and_index_elements(
        self, html_content: str, observation_id: str, page_state_fingerprint: str
    ) -> List[ElementRef]:
        elements: List[ElementRef] = []
        if not html_content or not html_content.strip():
            return elements

        soup = BeautifulSoup(html_content, "html.parser")

        # Find interactive elements (buttons, links, summary, tabs, inputs)
        interactive_tags = soup.find_all(
            ["a", "button", "summary", "input", "select", "textarea"],
            limit=BrowserConfig.MAX_INTERACTIVE_ELEMENTS,
        )

        for idx, tag in enumerate(interactive_tags):
            element_id = f"element_{idx + 1}"
            tag_name = tag.name.lower()
            role = tag.get("role", tag_name).lower()
            aria_label = tag.get("aria-label", "")
            visible_text = tag.get_text(" ", strip=True)[:100]

            accessible_name = aria_label or visible_text or tag.get("title", "") or tag.get("name", "")

            # Synthesize selector hint
            if tag.get("id"):
                selector_hint = f"#{tag['id']}"
            elif tag_name == "a" and tag.get("href"):
                selector_hint = f"a[href='{tag['href']}']"
            else:
                selector_hint = f"{tag_name}:nth-of-type({idx + 1})"

            is_input = tag_name in ("input", "textarea", "select")
            input_type = tag.get("type", "").lower() if tag_name == "input" else ""

            # Check basic safety flag
            is_safe = input_type not in ("submit", "password", "file", "credit-card")

            elem_ref = ElementRef(
                element_id=element_id,
                role=role,
                accessible_name=accessible_name,
                visible_text=visible_text,
                element_type=tag_name,
                selector_hint=selector_hint,
                observation_id=observation_id,
                page_state_fingerprint=page_state_fingerprint,
                is_interactive=True,
                is_safe=is_safe,
            )
            elements.append(elem_ref)

        return elements


element_selector = ElementSelector()
