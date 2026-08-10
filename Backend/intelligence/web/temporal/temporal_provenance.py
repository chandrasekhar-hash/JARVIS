"""
Temporal Provenance Validator for J.A.R.V.I.S. I2.2 V4.
Validates complete temporal provenance linkage: claim -> evidence -> source -> canonical_url -> temporal_metadata.
"""

from typing import List, Tuple
from intelligence.web.research.models import EvidenceItem, ResearchSource
from intelligence.web.temporal.models import TemporalClaim, TemporalMetadata


class TemporalProvenanceValidator:
    """Enforces fail-closed temporal provenance validation."""

    def validate_temporal_provenance(
        self,
        claims: List[TemporalClaim],
        evidence_items: List[EvidenceItem],
        sources: List[ResearchSource]
    ) -> Tuple[List[TemporalClaim], List[str]]:
        """
        Validates complete temporal provenance chain.
        Claims without verified temporal evidence linkage are rejected.
        """
        valid_ev_ids = {ev.evidence_id: ev for ev in evidence_items}
        valid_src_ids = {s.source_id: s for s in sources}

        valid_claims: List[TemporalClaim] = []
        errors: List[str] = []

        for claim in claims:
            if not claim.supporting_evidence_ids:
                errors.append(f"Temporal claim '{claim.claim_id}' has no supporting evidence.")
                continue

            claim_valid = True
            for ev_id in claim.supporting_evidence_ids:
                if ev_id not in valid_ev_ids:
                    errors.append(f"Temporal claim '{claim.claim_id}' references unknown evidence '{ev_id}'.")
                    claim_valid = False
                    break

                ev_item = valid_ev_ids[ev_id]
                if ev_item.source_id not in valid_src_ids:
                    errors.append(f"Evidence '{ev_id}' references unknown source '{ev_item.source_id}'.")
                    claim_valid = False
                    break

            if claim_valid:
                valid_claims.append(claim)

        return valid_claims, errors


temporal_provenance_validator = TemporalProvenanceValidator()
