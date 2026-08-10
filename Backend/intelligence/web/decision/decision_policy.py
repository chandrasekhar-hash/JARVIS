"""
Security Policy & Non-Overridable Server Hard Limits for J.A.R.V.I.S. I2.2 V11 Decision Intelligence.
"""
import time
from intelligence.web.decision.models import DecisionConfig, DecisionWebRequest


class ServerHardLimits:
    MAX_CANDIDATES = 20
    MAX_CRITERIA = 20
    MAX_REQUIREMENTS = 30
    MAX_EVIDENCE_PER_CRITERION = 6
    MAX_RECOMMENDATIONS = 5
    MAX_DECISION_CONTEXT_CHARS = 15000
    MAX_WALL_CLOCK_SECONDS = 12.0
    MAX_DECISION_SESSIONS_PER_CONVERSATION = 5


class DecisionPolicy:
    """
    Enforces security posture, wall-clock deadlines, and non-overridable server hard limits.
    """

    def sanitize_request(self, req: DecisionWebRequest) -> DecisionWebRequest:
        q = req.query.strip() if req.query else ""
        if len(q) > 1000:
            q = q[:1000]

        ev_ctx = req.evidence_context[: ServerHardLimits.MAX_CANDIDATES * 5]
        v_registry = req.verified_evidence_registry[: ServerHardLimits.MAX_CANDIDATES * 5] if req.verified_evidence_registry else None

        return DecisionWebRequest(
            query=q,
            evidence_context=ev_ctx,
            verified_evidence_registry=v_registry,
            conversation_id=req.conversation_id,
            owner_scope_id=req.owner_scope_id,
            decision_session_id=req.decision_session_id,
            user_timezone=req.user_timezone,
        )

    def check_deadline(self, start_time: float) -> bool:
        return (time.time() - start_time) > ServerHardLimits.MAX_WALL_CLOCK_SECONDS


decision_policy = DecisionPolicy()
