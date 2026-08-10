"""
Security Policy & Hard Limit Enforcement for J.A.R.V.I.S. I2.2 V9.
"""
import time
from typing import Optional
from intelligence.web.knowledge.models import KnowledgeWebRequest
from intelligence.web.knowledge.knowledge_graph import ServerHardLimits


class KnowledgePolicy:
    """
    Enforces security posture, wall-clock execution deadlines, and server hard limits.
    """

    def validate_and_sanitize_request(self, req: KnowledgeWebRequest) -> KnowledgeWebRequest:
        # Sanitize query
        sanitized_query = req.query.strip() if req.query else ""
        if len(sanitized_query) > 1000:
            sanitized_query = sanitized_query[:1000]

        # Enforce server hard limits on depth
        bounded_depth = min(max(1, req.max_depth), ServerHardLimits.MAX_GRAPH_DEPTH)

        # Clean URLs
        sanitized_urls = [u.strip() for u in req.urls if u and u.strip()]

        return KnowledgeWebRequest(
            query=sanitized_query,
            urls=sanitized_urls,
            conversation_id=req.conversation_id,
            owner_scope_id=req.owner_scope_id,
            max_depth=bounded_depth,
            user_timezone=req.user_timezone,
            force_refresh=req.force_refresh,
        )

    def check_deadline(self, start_time: float) -> bool:
        elapsed = time.time() - start_time
        return elapsed > ServerHardLimits.MAX_WALL_CLOCK_SECONDS


knowledge_policy = KnowledgePolicy()
