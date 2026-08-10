"""
J.A.R.V.I.S. Intelligence I2.2 V6 — Structured Record Selector.
Performs query-aware selection of relevant records using deterministic keyword overlap,
heading relevance, schema types, and field-name matching.
"""
import re
import logging
from typing import List, Set
from intelligence.web.structured.models import (
    StructuredRecord,
    StructuredConfig,
)

logger = logging.getLogger("JARVIS_StructuredSelector")


class StructuredSelector:
    """
    Selects relevant structured records for a given user query deterministically.
    """

    def select_relevant_records(
        self, query: str, records: List[StructuredRecord]
    ) -> List[StructuredRecord]:
        if not records:
            return []

        if not query or not query.strip():
            # Return up to MAX_SELECTED_RECORDS default
            return records[: StructuredConfig.MAX_SELECTED_RECORDS]

        query_tokens = set(re.findall(r"\b\w{3,}\b", query.lower()))

        scored_records = []
        for record in records:
            score = 0
            # 1. Schema type match
            if record.schema_type and record.schema_type.lower() in query.lower():
                score += 5

            # 2. Field names match
            for field in record.fields:
                f_name = field.name.lower()
                f_val = field.value.lower()

                for token in query_tokens:
                    if token in f_name:
                        score += 3
                    if token in f_val:
                        score += 1

            if score > 0:
                scored_records.append((score, record))

        # Sort by score descending
        scored_records.sort(key=lambda x: x[0], reverse=True)

        selected = [r[1] for r in scored_records[: StructuredConfig.MAX_SELECTED_RECORDS]]
        if not selected:
            # Fallback if no keyword matches: return top records
            selected = records[: StructuredConfig.MAX_SELECTED_RECORDS]

        return selected


structured_selector = StructuredSelector()
