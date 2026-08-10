"""
J.A.R.V.I.S. Intelligence I2.2 V6 — Semantic List Extractor.
Extracts repeated semantic lists (release versions, pricing, events, features)
while strictly rejecting navigation lists (e.g., Home, About, Contact).
"""
import re
import logging
from typing import List, Dict, Any
from bs4 import BeautifulSoup, Tag

from intelligence.web.structured.models import (
    StructuredRecord,
    StructuredField,
    StructuredDataset,
    StructuredDataType,
    StructuredConfig,
)

logger = logging.getLogger("JARVIS_ListExtractor")

NAV_KEYWORDS = {"home", "about", "contact", "privacy", "terms", "login", "signup", "register", "careers", "help", "faq"}


class ListExtractor:
    """
    Parses semantic lists from HTML documents, identifying data patterns vs navigation.
    """

    def extract_lists(
        self, html_content: str, source_id: str, canonical_url: str
    ) -> List[StructuredDataset]:
        datasets: List[StructuredDataset] = []
        if not html_content or not html_content.strip():
            return datasets

        soup = BeautifulSoup(html_content, "html.parser")
        list_tags = soup.find_all(["ul", "ol", "dl"])

        valid_list_count = 0
        for l_idx, tag in enumerate(list_tags):
            if valid_list_count >= 5:  # Cap at top 5 list candidates
                break

            items = tag.find_all(["li", "dt", "dd"])
            if len(items) < 2:  # Need at least 2 items for a list
                continue

            # Check if this is a navigation list
            item_texts = [item.get_text(" ", strip=True) for item in items]
            if self._is_navigation_list(item_texts):
                continue

            # Check if semantic pattern exists (versions, dates, prices, structured key-values)
            if not self._has_semantic_pattern(item_texts):
                continue

            valid_list_count += 1
            dataset_id = f"list_{l_idx}_{source_id}"

            records: List[StructuredRecord] = []
            for item_idx, item_text in enumerate(item_texts):
                if item_idx >= StructuredConfig.MAX_TABLE_ROWS:
                    break

                source_path = f"list[{l_idx}].item[{item_idx}]"
                field = StructuredField(
                    name="item",
                    value=item_text,
                    source_path=source_path,
                    source_id=source_id,
                )
                record = StructuredRecord(
                    record_id=f"{dataset_id}_item_{item_idx}",
                    record_type=StructuredDataType.STRUCTURED_LIST,
                    fields=[field],
                    source_id=source_id,
                    canonical_url=canonical_url,
                    extraction_method="BS4_SEMANTIC_LIST",
                )
                records.append(record)

            dataset = StructuredDataset(
                dataset_id=dataset_id,
                title=f"Semantic List {valid_list_count}",
                columns=["item"],
                records=records,
                source_id=source_id,
                canonical_url=canonical_url,
                data_type=StructuredDataType.STRUCTURED_LIST,
                total_records_detected=len(item_texts),
                records_returned=len(records),
            )
            datasets.append(dataset)

        return datasets

    def _is_navigation_list(self, item_texts: List[str]) -> bool:
        nav_matches = 0
        for text in item_texts:
            t_lower = text.lower().strip()
            if any(k == t_lower for k in NAV_KEYWORDS) or len(t_lower) < 3:
                nav_matches += 1
        return nav_matches >= len(item_texts) * 0.5

    def _has_semantic_pattern(self, item_texts: List[str]) -> bool:
        pattern_matches = 0
        # Version pattern e.g. 3.14.0, v1.2, Dec 2026, $99, etc.
        pattern = re.compile(
            r"(\bv?\d+\.\d+(\.\d+)?\b|\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{4})\b|\$\d+)",
            re.IGNORECASE,
        )
        for text in item_texts:
            if pattern.search(text) or ":" in text or "-" in text:
                pattern_matches += 1
        return pattern_matches >= 1


list_extractor = ListExtractor()
