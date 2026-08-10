"""
Internal Answer Consistency Engine for J.A.R.V.I.S. I2.2 V10.
"""
import re
from typing import List
from intelligence.web.verification.models import ExtractedClaim, VerificationFinding


class AnswerConsistencyChecker:
    """
    Scans the draft answer claims for internal self-contradictions (e.g. conflicting versions,
    conflicting prices, conflicting release dates).
    """

    def check_internal_consistency(
        self, claims: List[ExtractedClaim]
    ) -> List[VerificationFinding]:
        findings: List[VerificationFinding] = []
        if len(claims) < 2:
            return findings

        # 1. Version conflict check
        versions_seen = {}
        for c in claims:
            vers = re.findall(r"\bv?(\d+\.\d+(?:\.\d+)?)\b", c.text)
            for v in vers:
                if "version" in c.text.lower() or "release" in c.text.lower():
                    if versions_seen and v not in versions_seen:
                        # Internal version conflict detected!
                        first_cid, first_v = next(iter(versions_seen.items()))
                        findings.append(
                            VerificationFinding(
                                finding_id=f"f_inc_ver_{c.claim_id}",
                                claim_id=c.claim_id,
                                finding_type="INTERNAL_VERSION_CONTRADICTION",
                                description=f"Draft answer contains conflicting version claims: {first_v} vs {v}.",
                                suggested_action="QUALIFY",
                            )
                        )
                    versions_seen[c.claim_id] = v

        # 2. Price conflict check
        prices_seen = {}
        for c in claims:
            prices = re.findall(r"\$\d+(?:\.\d+)?", c.text)
            for p in prices:
                if prices_seen and p not in prices_seen:
                    first_cid, first_p = next(iter(prices_seen.items()))
                    findings.append(
                        VerificationFinding(
                            finding_id=f"f_inc_price_{c.claim_id}",
                            claim_id=c.claim_id,
                            finding_type="INTERNAL_PRICE_CONTRADICTION",
                            description=f"Draft answer contains conflicting price claims: {first_p} vs {p}.",
                            suggested_action="QUALIFY",
                        )
                    )
                prices_seen[c.claim_id] = p

        return findings


answer_consistency_checker = AnswerConsistencyChecker()
