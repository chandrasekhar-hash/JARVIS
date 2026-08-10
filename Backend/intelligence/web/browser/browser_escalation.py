"""
J.A.R.V.I.S. Intelligence I2.2 V7 — Static-First Browser Escalation Policy.
Evaluates whether static V2 retrieval is sufficient or if V7 browser escalation is required.
Static fetch is ALWAYS attempted first. Browser execution occurs ONLY when explicit evidence warrants it.
"""
import logging
from typing import Tuple
from intelligence.web.browser.models import BrowserEscalationReason

logger = logging.getLogger("JARVIS_BrowserEscalation")

ESCALATION_KEYWORDS = {
    "expand", "accordion", "click", "interact", "dynamic", "javascript-only",
    "load more", "next page", "spa", "client-side", "rendered", "tab"
}


class BrowserEscalationPolicy:
    """
    Evaluates browser escalation requests against static fetch baselines and explicit query intent.
    """

    def evaluate_escalation(
        self, query: str, static_status: str = "SUCCESS", static_content: str = ""
    ) -> Tuple[bool, BrowserEscalationReason]:
        query_lower = query.lower()

        # 1. Explicit user request for dynamic interaction
        if any(kw in query_lower for kw in ESCALATION_KEYWORDS):
            return True, BrowserEscalationReason.EXPLICIT_USER_REQUEST

        # 2. Static V2 retrieval returned JS_RENDER_REQUIRED
        if static_status in ("JS_RENDER_REQUIRED", "EMPTY_CONTENT"):
            return True, BrowserEscalationReason.JS_RENDER_REQUIRED

        # 3. Static content is usable -> No escalation required!
        if static_content and len(static_content.strip()) > 200:
            return False, BrowserEscalationReason.NONE

        return False, BrowserEscalationReason.NONE


browser_escalation_policy = BrowserEscalationPolicy()
