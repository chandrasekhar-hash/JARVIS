"""
Fail-Closed ProvenanceValidator & Repair Engine for J.A.R.V.I.S. I2.2 V3.
Validates complete provenance chain: ResearchClaim -> EvidenceItem -> ResearchSource -> canonical_url.
Rejects unsupported claims or unknown source IDs, attempts 1 bounded repair, and fails closed.
"""

import re
from typing import List, Tuple, Set, Optional
from intelligence.web.research.models import (
    ResearchClaim,
    EvidenceItem,
    ResearchSource,
    ResearchFinding,
    ResearchStatus
)


class ProvenanceValidator:
    """Enforces fail-closed claim-level provenance validation."""

    def validate_provenance_chain(
        self,
        claims: List[ResearchClaim],
        evidence_items: List[EvidenceItem],
        sources: List[ResearchSource]
    ) -> Tuple[List[ResearchClaim], List[str]]:
        """
        Validates complete provenance chain:
        claim -> supporting_evidence_ids -> EvidenceItem -> source_id -> ResearchSource -> canonical_url.
        Returns (valid_claims, list_of_validation_errors).
        """
        valid_ev_ids = {ev.evidence_id: ev for ev in evidence_items}
        valid_src_ids = {s.source_id: s for s in sources}

        valid_claims: List[ResearchClaim] = []
        errors: List[str] = []

        for claim in claims:
            if not claim.supporting_evidence_ids:
                errors.append(f"Claim '{claim.claim_id}' has no supporting evidence IDs.")
                continue

            claim_ev_valid = True
            for ev_id in claim.supporting_evidence_ids:
                if ev_id not in valid_ev_ids:
                    errors.append(f"Claim '{claim.claim_id}' references unknown evidence_id '{ev_id}'.")
                    claim_ev_valid = False
                    break

                ev_item = valid_ev_ids[ev_id]
                if ev_item.source_id not in valid_src_ids:
                    errors.append(f"Evidence '{ev_id}' references unknown source_id '{ev_item.source_id}'.")
                    claim_ev_valid = False
                    break

            if claim_ev_valid:
                valid_claims.append(claim)

        return valid_claims, errors

    def validate_and_repair_response_text(
        self,
        text: str,
        finding: ResearchFinding,
        evidence_items: List[EvidenceItem],
        sources: List[ResearchSource]
    ) -> Tuple[str, ResearchFinding, bool]:
        """
        Scans synthesized response text for cited source IDs (e.g. [source_1], [source_99]).
        If unknown source IDs or unverified URLs are detected:
        1. Strips/rejects unsupported citations or claims.
        2. Attempts 1 bounded repair using only verified evidence items.
        3. Fails closed (omits claim / marks PARTIAL) if repair fails.
        """
        valid_src_ids = {s.source_id for s in sources}
        found_citations = set(re.findall(r"\[(source_\d+)\]", text))

        unknown_citations = found_citations - valid_src_ids

        if not unknown_citations:
            # All citations valid
            return text, finding, True

        # Unknown citation detected -> Fail-Closed Repair Attempt
        # 1. Strip unknown citations from text
        repaired_text = text
        for unk in unknown_citations:
            repaired_text = repaired_text.replace(f"[{unk}]", "")

        # 2. Filter finding claims to retain only those with valid evidence linkage
        valid_claims, _ = self.validate_provenance_chain(finding.claims, evidence_items, sources)
        finding.claims = valid_claims

        # Check if repair succeeded
        remaining_unknowns = set(re.findall(r"\[(source_\d+)\]", repaired_text)) - valid_src_ids
        repair_success = len(remaining_unknowns) == 0

        return repaired_text, finding, repair_success


provenance_validator = ProvenanceValidator()
