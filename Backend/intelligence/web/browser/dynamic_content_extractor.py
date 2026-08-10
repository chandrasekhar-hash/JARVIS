"""
J.A.R.V.I.S. Intelligence I2.2 V7 — Dynamic Content Extractor.
Extracts rendered visible content from browser DOM and composes V6 structured extractors (HTML tables, JSON-LD, semantic lists).
"""
import logging
from typing import List, Dict, Any, Tuple
from intelligence.web.structured.table_extractor import table_extractor
from intelligence.web.structured.jsonld_extractor import jsonld_extractor
from intelligence.web.structured.list_extractor import list_extractor
from intelligence.web.structured.models import StructuredDataset, StructuredRecord

logger = logging.getLogger("JARVIS_DynamicContentExtractor")


class DynamicContentExtractor:
    """
    Extracts rendered dynamic page content and composes V6 structured data extraction.
    """

    def extract_dynamic_content(
        self, rendered_html: str, source_id: str, canonical_url: str
    ) -> Tuple[List[StructuredDataset], List[StructuredRecord]]:
        datasets: List[StructuredDataset] = []
        records: List[StructuredRecord] = []

        if not rendered_html or not rendered_html.strip():
            return datasets, records

        # 1. Compose V6 HTML Table Extractor on rendered HTML
        tables = table_extractor.extract_tables(rendered_html, source_id, canonical_url)
        datasets.extend(tables)
        for ds in tables:
            records.extend(ds.records)

        # 2. Compose V6 JSON-LD Extractor on rendered HTML
        jsonld_recs = jsonld_extractor.extract_jsonld(rendered_html, source_id, canonical_url)
        records.extend(jsonld_recs)

        # 3. Compose V6 Semantic List Extractor on rendered HTML
        lists = list_extractor.extract_lists(rendered_html, source_id, canonical_url)
        datasets.extend(lists)
        for ds in lists:
            records.extend(ds.records)

        return datasets, records


dynamic_content_extractor = DynamicContentExtractor()
