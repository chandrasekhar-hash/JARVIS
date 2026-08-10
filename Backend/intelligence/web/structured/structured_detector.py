"""
J.A.R.V.I.S. Intelligence I2.2 V6 — Structured Data Detector.
Deterministically detects structured data formats present in retrieved web content.
"""
import re
from typing import List, Dict, Any, Set
from intelligence.web.structured.models import StructuredDataType


class StructuredDataDetector:
    """
    Analyzes HTML or raw content bodies to identify available structured formats deterministically.
    """

    def detect_formats(self, html_or_text: str, content_type: str = "") -> Set[StructuredDataType]:
        detected: Set[StructuredDataType] = set()
        if not html_or_text or not html_or_text.strip():
            return detected

        ct_lower = content_type.lower()

        # 1. JSON Content-Type or Body
        if "application/json" in ct_lower or "text/json" in ct_lower:
            detected.add(StructuredDataType.JSON)
        elif html_or_text.strip().startswith(("{", "[")):
            detected.add(StructuredDataType.JSON)

        # 2. JSON-LD in HTML (<script type="application/ld+json">)
        if 'type="application/ld+json"' in html_or_text.lower() or "type='application/ld+json'" in html_or_text.lower():
            detected.add(StructuredDataType.JSON_LD)

        # 3. HTML Tables
        if "<table" in html_or_text.lower():
            detected.add(StructuredDataType.HTML_TABLE)

        # 4. RSS / Atom Feeds
        if "<rss" in html_or_text.lower() or "application/rss+xml" in ct_lower:
            detected.add(StructuredDataType.RSS)
        if "<feed" in html_or_text.lower() and ("xmlns=\"http://www.w3.org/2005/Atom\"" in html_or_text or "application/atom+xml" in ct_lower):
            detected.add(StructuredDataType.ATOM)

        # 5. Semantic Lists / Repeated Structures
        if "<ul" in html_or_text.lower() or "<ol" in html_or_text.lower() or "<dl" in html_or_text.lower():
            detected.add(StructuredDataType.STRUCTURED_LIST)

        # 6. Pagination controls
        if 'rel="next"' in html_or_text.lower() or 'rel="prev"' in html_or_text.lower() or "page=" in html_or_text.lower():
            detected.add(StructuredDataType.PAGINATION)

        # 7. Resource links (.pdf, .csv, .json, .xml, .zip)
        resource_extensions = [".pdf", ".csv", ".json", ".xml", ".zip", ".xlsx"]
        if any(ext in html_or_text.lower() for ext in resource_extensions):
            detected.add(StructuredDataType.DOWNLOADABLE_RESOURCE)

        return detected


structured_detector = StructuredDataDetector()
