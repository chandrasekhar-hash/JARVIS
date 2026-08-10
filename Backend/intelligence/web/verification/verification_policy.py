"""
Security Policy & Non-Overridable Server Hard Limits for J.A.R.V.I.S. I2.2 V10.
"""
import time
from typing import Optional
from intelligence.web.verification.models import VerificationWebRequest


class ServerHardLimits:
    MAX_CLAIMS_PER_ANSWER = 30
    MAX_CITATIONS_PER_CLAIM = 8
    MAX_EVIDENCE_ITEMS_PER_CLAIM = 8
    MAX_VERIFICATION_CONTEXT_CHARS = 15000
    MAX_REPAIR_ATTEMPTS = 1
    MAX_VERIFICATION_SECONDS = 8.0
    MAX_TOTAL_VERIFICATION_FINDINGS = 100


class VerificationPolicy:
    """
    Enforces security posture, wall-clock deadlines, and non-overridable server hard limits.
    """

    def sanitize_request(self, req: VerificationWebRequest) -> VerificationWebRequest:
        draft = req.draft_answer.strip() if req.draft_answer else ""
        if len(draft) > 50000:
            draft = draft[:50000]

        query = req.query.strip() if req.query else ""
        if len(query) > 1000:
            query = query[:1000]

        # Truncate evidence items if exceeding limits
        bounded_evidence = req.evidence_context[: ServerHardLimits.MAX_TOTAL_VERIFICATION_FINDINGS]

        return VerificationWebRequest(
            draft_answer=draft,
            evidence_context=bounded_evidence,
            query=query,
            conversation_id=req.conversation_id,
            owner_scope_id=req.owner_scope_id,
            user_timezone=req.user_timezone,
        )

    def check_deadline(self, start_time: float) -> bool:
        elapsed = time.time() - start_time
        return elapsed > ServerHardLimits.MAX_VERIFICATION_SECONDS


verification_policy = VerificationPolicy()
