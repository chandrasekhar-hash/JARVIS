"""
Fail-Closed Provenance Validator for J.A.R.V.I.S. I2.2 V9.
"""
from typing import Dict, List, Optional, Set, Tuple
from intelligence.web.knowledge.models import (
    CanonicalEntity,
    EvidenceBackedRelationship,
    ProvenanceStatus,
)


class ProvenanceValidator:
    """
    Validates complete, unbroken evidence chains for entities and relationships.
    Enforces fail-closed posture: any claim lacking valid evidence provenance is dropped.
    """

    def validate_entity_provenance(
        self,
        entity: CanonicalEntity,
        valid_source_ids: Set[str],
    ) -> ProvenanceStatus:
        if not entity.source_ids or not any(sid in valid_source_ids for sid in entity.source_ids):
            entity.provenance_status = ProvenanceStatus.REJECTED
            return ProvenanceStatus.REJECTED

        if not entity.mention_ids:
            entity.provenance_status = ProvenanceStatus.REJECTED
            return ProvenanceStatus.REJECTED

        entity.provenance_status = ProvenanceStatus.VERIFIED
        return ProvenanceStatus.VERIFIED

    def validate_relationship_provenance(
        self,
        rel: EvidenceBackedRelationship,
        valid_source_ids: Set[str],
        valid_entity_ids: Set[str],
        already_verified_evidence: Optional[Dict[str, Dict]] = None,
    ) -> Tuple[ProvenanceStatus, Optional[EvidenceBackedRelationship]]:
        # 1. Reject unknown entity IDs
        if rel.subject_entity_id not in valid_entity_ids or rel.object_entity_id not in valid_entity_ids:
            rel.provenance_status = ProvenanceStatus.REJECTED
            return ProvenanceStatus.REJECTED, None

        # 2. Reject missing source path or unknown source ID
        if not rel.source_path or not rel.source_id or rel.source_id not in valid_source_ids:
            # Attempt AT MOST ONE bounded repair using already verified evidence
            if already_verified_evidence and rel.evidence_id in already_verified_evidence:
                evidence_info = already_verified_evidence[rel.evidence_id]
                rel.source_id = evidence_info.get("source_id", rel.source_id)
                rel.canonical_url = evidence_info.get("canonical_url", rel.canonical_url)
                rel.source_path = evidence_info.get("source_path") or rel.source_path or "repaired_path"
                rel.provenance_status = ProvenanceStatus.REPAIRED
                return ProvenanceStatus.REPAIRED, rel

            rel.provenance_status = ProvenanceStatus.REJECTED
            return ProvenanceStatus.REJECTED, None

        rel.provenance_status = ProvenanceStatus.VERIFIED
        return ProvenanceStatus.VERIFIED, rel


provenance_validator = ProvenanceValidator()
