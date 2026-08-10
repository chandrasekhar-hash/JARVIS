"""
J.A.R.V.I.S. Intelligence I2.2 V6 — Structured Provenance Engine.
Validates fail-closed provenance traces for all structured records and fields.
Every factual structured value MUST trace claim -> StructuredRecord -> StructuredField -> source_id -> canonical_url -> source_path.
"""
import logging
from typing import List, Dict, Any
from intelligence.web.structured.models import StructuredRecord, StructuredField

logger = logging.getLogger("JARVIS_StructuredProvenance")


class StructuredProvenanceEngine:
    """
    Ensures complete fail-closed provenance chains for structured records.
    """

    def validate_provenance(self, records: List[StructuredRecord]) -> List[Dict[str, Any]]:
        provenance_chain: List[Dict[str, Any]] = []

        for record in records:
            if not record.source_id or not record.canonical_url:
                record.provenance_status = "INVALID_MISSING_SOURCE"
                continue

            valid_fields = []
            for field in record.fields:
                if not field.source_path or not field.source_path.strip():
                    logger.warning(f"Field '{field.name}' in record '{record.record_id}' missing source_path")
                    continue
                valid_fields.append({
                    "field_name": field.name,
                    "value": field.value,
                    "normalized_value": field.normalized_value,
                    "source_path": field.source_path,
                })

            if not valid_fields:
                record.provenance_status = "INVALID_NO_VALID_FIELDS"
                continue

            record.provenance_status = "VALID"
            provenance_chain.append({
                "record_id": record.record_id,
                "record_type": record.record_type.value,
                "source_id": record.source_id,
                "canonical_url": record.canonical_url,
                "schema_type": record.schema_type,
                "is_malformed": record.is_malformed,
                "fields": valid_fields,
            })

        return provenance_chain


structured_provenance_engine = StructuredProvenanceEngine()
