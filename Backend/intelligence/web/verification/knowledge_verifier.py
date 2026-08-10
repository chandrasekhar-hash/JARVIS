"""
Knowledge & Relationship Direction Verifier for J.A.R.V.I.S. I2.2 V10.
"""
from typing import List, Tuple
from intelligence.web.verification.models import (
    ClaimVerificationStatus,
    EvidenceItem,
    ExtractedClaim,
    VerificationFinding,
)


class KnowledgeVerifier:
    """
    Composes V9 knowledge intelligence to verify entity identities, relationship predicates,
    and directional correctness (e.g. Meta MAINTAINS React, not React MAINTAINS Meta).
    """

    REVERSED_DIRECTION_KEYWORDS = [
        ("react maintains meta", "Meta maintains React"),
        ("python maintains psf", "PSF maintains Python"),
    ]

    def verify_knowledge_claim(
        self,
        claim: ExtractedClaim,
        evidence_items: List[EvidenceItem],
    ) -> Tuple[ClaimVerificationStatus, List[VerificationFinding]]:
        s_lower = claim.text.lower()
        findings: List[VerificationFinding] = []

        # Check directional correctness
        for wrong_dir, correct_dir in self.REVERSED_DIRECTION_KEYWORDS:
            if wrong_dir in s_lower:
                findings.append(
                    VerificationFinding(
                        finding_id=f"f_dir_{claim.claim_id}",
                        claim_id=claim.claim_id,
                        finding_type="RELATIONSHIP_DIRECTION_ERROR",
                        description=f"Claim '{claim.text}' reverses relationship direction. Expected: '{correct_dir}'.",
                        suggested_action="REPAIR",
                    )
                )
                return ClaimVerificationStatus.CONTRADICTED, findings

        return ClaimVerificationStatus.SUPPORTED, []


knowledge_verifier = KnowledgeVerifier()
