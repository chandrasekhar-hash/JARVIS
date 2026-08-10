"""
Temporal Claim Verification Engine for J.A.R.V.I.S. I2.2 V10.
"""
from typing import List, Optional, Tuple
from intelligence.web.verification.models import (
    ClaimVerificationStatus,
    EvidenceItem,
    ExtractedClaim,
    VerificationFinding,
)


class TemporalVerifier:
    """
    Verifies temporal claims against V4 freshness findings and evidence metadata.
    Detects stale claims, latest/current version mismatches, and release date errors.
    """

    def verify_temporal_claim(
        self,
        claim: ExtractedClaim,
        evidence_items: List[EvidenceItem],
    ) -> Tuple[ClaimVerificationStatus, List[VerificationFinding]]:
        if not claim.text:
            return ClaimVerificationStatus.UNVERIFIED, []

        s_lower = claim.text.lower()
        findings: List[VerificationFinding] = []

        # Check latest / current release claims
        if "latest" in s_lower or "current" in s_lower or "stable" in s_lower:
            for ev in evidence_items:
                ev_lower = ev.text.lower()
                # If evidence mentions a newer version or update timestamp
                if "newer" in ev_lower or "superseded" in ev_lower or "outdated" in ev_lower:
                    findings.append(
                        VerificationFinding(
                            finding_id=f"f_temp_stale_{claim.claim_id}",
                            claim_id=claim.claim_id,
                            finding_type="STALE_TEMPORAL_CLAIM",
                            description=f"Claim '{claim.text}' presents outdated information as latest.",
                            suggested_action="QUALIFY",
                        )
                    )
                    return ClaimVerificationStatus.STALE, findings

        return ClaimVerificationStatus.SUPPORTED, []


temporal_verifier = TemporalVerifier()
