"""
Citation Validator Engine for J.A.R.V.I.S. I2.2 V10.
"""
from typing import Dict, List, Optional, Tuple
from intelligence.web.verification.models import (
    CitationItem,
    CitationVerificationStatus,
    EvidenceItem,
    ExtractedClaim,
    VerificationFinding,
)


class CitationValidator:
    """
    Validates inline citations against verified evidence provenance and checks if the cited source
    actually supports the claim text (detecting CITATION_MISMATCH).
    """

    def validate_citations_for_claim(
        self,
        claim: ExtractedClaim,
        evidence_registry: Dict[str, EvidenceItem],
    ) -> Tuple[CitationVerificationStatus, List[VerificationFinding]]:
        if not claim.citations:
            return CitationVerificationStatus.MISSING, []

        findings: List[VerificationFinding] = []
        has_valid = False
        has_invalid_or_forged = False
        has_mismatch = False

        for cit in claim.citations:
            if cit.resolution_status in (CitationVerificationStatus.INVALID, CitationVerificationStatus.FORGED):
                has_invalid_or_forged = True
                findings.append(
                    VerificationFinding(
                        finding_id=f"f_cit_{cit.citation_id}",
                        claim_id=claim.claim_id,
                        finding_type="INVALID_CITATION",
                        description=f"Citation '{cit.raw_text}' is invalid, unmapped, or forged.",
                        suggested_action="REMOVE",
                    )
                )
                continue

            if not cit.source_id or cit.source_id not in evidence_registry:
                has_invalid_or_forged = True
                findings.append(
                    VerificationFinding(
                        finding_id=f"f_cit_src_{cit.citation_id}",
                        claim_id=claim.claim_id,
                        finding_type="UNKNOWN_SOURCE_ID",
                        description=f"Citation '{cit.raw_text}' references unknown source_id '{cit.source_id}'.",
                        suggested_action="REMOVE",
                    )
                )
                continue

            # Check if source supports claim (detecting CITATION_MISMATCH)
            evidence_item = evidence_registry[cit.source_id]
            if not self._source_supports_claim(claim.text, evidence_item.text):
                has_mismatch = True
                findings.append(
                    VerificationFinding(
                        finding_id=f"f_mismatch_{cit.citation_id}",
                        claim_id=claim.claim_id,
                        finding_type="CITATION_MISMATCH",
                        description=f"Citation '{cit.raw_text}' points to real source '{cit.source_id}' but the source text does not support the claim.",
                        suggested_action="QUALIFY",
                    )
                )
            else:
                has_valid = True

        if has_mismatch:
            return CitationVerificationStatus.MISMATCHED, findings
        if has_invalid_or_forged and not has_valid:
            return CitationVerificationStatus.FORGED, findings
        if has_valid and not has_invalid_or_forged:
            return CitationVerificationStatus.VALID, findings
        if has_valid and has_invalid_or_forged:
            return CitationVerificationStatus.VALID, findings

        return CitationVerificationStatus.INVALID, findings

    def _source_supports_claim(self, claim_text: str, source_text: str) -> bool:
        if not source_text:
            return False

        # Lexical matching heuristic
        c_words = set(re.findall(r"\w+", claim_text.lower()))
        s_words = set(re.findall(r"\w+", source_text.lower()))

        # Remove stop words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "and", "or", "in", "of", "to", "for", "with", "by", "this", "that"}
        c_significant = c_words - stop_words
        if not c_significant:
            return True

        intersection = c_significant.intersection(s_words)
        match_ratio = len(intersection) / len(c_significant)
        return match_ratio >= 0.3


import re

citation_validator = CitationValidator()
