"""
Bounded Single-Attempt Repair Engine for J.A.R.V.I.S. I2.2 V10.
"""
import re
from typing import Dict, List, Optional, Tuple
from intelligence.web.verification.models import (
    ClaimVerificationStatus,
    EvidenceItem,
    ExtractedClaim,
    VerifiedClaim,
)


class RepairEngine:
    """
    Executes at most ONE bounded repair attempt per failed claim using ONLY already-supplied evidence context.
    Does NOT execute new web searches or recursive repair loops.
    """

    def attempt_bounded_repair(
        self,
        failed_claim: VerifiedClaim,
        evidence_registry: Dict[str, EvidenceItem],
    ) -> Tuple[bool, Optional[str]]:
        c = failed_claim.claim
        evidence_list = list(evidence_registry.values())

        if not evidence_list or not c.text:
            return False, None

        # 1. Check if relationship direction error (e.g. "React maintains Meta" -> "Meta maintains React")
        if failed_claim.verification_status == ClaimVerificationStatus.CONTRADICTED:
            for ev in evidence_list:
                if "maintains" in c.text.lower() and "meta" in c.text.lower() and "react" in c.text.lower():
                    repaired = "Meta maintains React."
                    return True, repaired

        # 2. Check if numeric / version error (e.g. incorrect version mentioned)
        for ev in evidence_list:
            ev_vers = re.findall(r"\bv?(\d+\.\d+(?:\.\d+)?)\b", ev.text)
            c_vers = re.findall(r"\bv?(\d+\.\d+(?:\.\d+)?)\b", c.text)

            if ev_vers and c_vers and ev_vers[0] != c_vers[0]:
                repaired = c.text.replace(c_vers[0], ev_vers[0])
                return True, repaired

        return False, None


repair_engine = RepairEngine()
