"""
Alias Management and Resolution with Provenance for J.A.R.V.I.S. I2.2 V9.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from intelligence.web.knowledge.models import ProvenanceStatus


@dataclass
class AliasRecord:
    alias: str
    normalized_alias: str
    canonical_entity_id: str
    source_id: str
    canonical_url: Optional[str] = None
    evidence_id: Optional[str] = None
    alias_type: str = "ALTERNATE_NAME"  # ALTERNATE_NAME, ABBREVIATION, HISTORICAL, REPO_PACKAGE, URL_ALIAS
    provenance_status: ProvenanceStatus = ProvenanceStatus.UNVERIFIED


class AliasResolver:
    """
    Manages and resolves entity aliases while preserving evidence provenance.
    """

    def __init__(self):
        # Map normalized_alias -> List[AliasRecord]
        self._alias_registry: Dict[str, List[AliasRecord]] = {}

    def register_alias(
        self,
        alias: str,
        normalized_alias: str,
        canonical_entity_id: str,
        source_id: str,
        canonical_url: Optional[str] = None,
        evidence_id: Optional[str] = None,
        alias_type: str = "ALTERNATE_NAME",
        provenance_status: ProvenanceStatus = ProvenanceStatus.UNVERIFIED,
    ) -> AliasRecord:
        record = AliasRecord(
            alias=alias,
            normalized_alias=normalized_alias,
            canonical_entity_id=canonical_entity_id,
            source_id=source_id,
            canonical_url=canonical_url,
            evidence_id=evidence_id,
            alias_type=alias_type,
            provenance_status=provenance_status,
        )

        records = self._alias_registry.setdefault(normalized_alias, [])
        # Avoid duplicate exact records
        for existing in records:
            if existing.canonical_entity_id == canonical_entity_id and existing.alias == alias:
                return existing

        records.append(record)
        return record

    def resolve_alias_to_entity_ids(self, normalized_alias: str) -> List[str]:
        records = self._alias_registry.get(normalized_alias, [])
        entity_ids: Set[str] = set()
        for r in records:
            entity_ids.add(r.canonical_entity_id)
        return list(entity_ids)

    def get_aliases_for_entity(self, canonical_entity_id: str) -> List[AliasRecord]:
        result = []
        for records in self._alias_registry.values():
            for r in records:
                if r.canonical_entity_id == canonical_entity_id:
                    result.append(r)
        return result

    def clear(self):
        self._alias_registry.clear()


alias_resolver = AliasResolver()
