"""
J.A.R.V.I.S. Intelligence I2.2 V7 — Browser Action Safety Policy.
Classifies browser actions into SideEffectClass based on DOM element semantics (element type, form association, href, input type, attributes).
Enforces strict read-only safety: form submissions, logins, file uploads, purchases, and deletions are rejected.
Fails closed on unknown/ambiguous element semantics.
"""
import logging
from typing import Tuple, Dict, Any, Optional

from intelligence.web.browser.models import (
    BrowserActionType,
    SideEffectClass,
    ElementRef,
)

logger = logging.getLogger("JARVIS_BrowserPolicy")

FORBIDDEN_KEYWORDS = {
    "submit", "login", "signin", "password", "buy", "purchase", "checkout",
    "pay", "delete", "remove", "upload", "file", "post", "send", "message", "subscribe"
}


class BrowserActionPolicy:
    """
    Evaluates action safety and side-effect classifications based on DOM semantics.
    """

    def classify_action_safety(
        self, action_type: BrowserActionType, element: Optional[ElementRef] = None, tag_info: Optional[Dict[str, Any]] = None
    ) -> Tuple[SideEffectClass, str, bool]:
        """
        Returns (SideEffectClass, reason, is_allowed).
        """

        # 1. Read-only navigation / scroll / observe actions
        if action_type in (
            BrowserActionType.OPEN_PAGE,
            BrowserActionType.OBSERVE,
            BrowserActionType.SCROLL,
            BrowserActionType.WAIT_FOR_DYNAMIC_CONTENT,
        ):
            return SideEffectClass.READ_ONLY, "Safe read-only action", True

        if not element:
            return SideEffectClass.UNKNOWN, "Action missing element target", False

        # 2. Check DOM semantics
        tag_name = (tag_info.get("tag_name") if tag_info else element.element_type).lower()
        input_type = (tag_info.get("type") if tag_info else "").lower()
        role = (element.role or "").lower()
        name_text = (element.accessible_name or element.visible_text or "").lower()
        is_form_child = tag_info.get("in_form", False) if tag_info else False

        # Check for File Upload
        if input_type == "file" or "upload" in name_text:
            return SideEffectClass.DESTRUCTIVE, "File upload inputs forbidden in V7", False

        # Check for Form Submissions / Submit Buttons
        if input_type in ("submit", "password", "credit-card") or tag_name == "form" or is_form_child:
            return SideEffectClass.FORM_MUTATION, "Form submission or mutation controls rejected", False

        # Check for Forbidden Keyword Matches in Semantics
        if any(kw in name_text for kw in FORBIDDEN_KEYWORDS):
            return SideEffectClass.ACCOUNT_MUTATION, f"Forbidden action keyword detected in element semantics: '{name_text}'", False

        # 3. Safe Accordion Expand / Tab Click / Load More / Next Page
        if action_type in (
            BrowserActionType.EXPAND,
            BrowserActionType.OPEN_TAB_CONTENT,
            BrowserActionType.LOAD_MORE,
            BrowserActionType.NEXT_PAGE,
            BrowserActionType.SELECT_NON_SENSITIVE_FILTER,
            BrowserActionType.CLICK_SAFE,
        ):
            if role in ("button", "tab", "link", "heading", "summary") or tag_name in ("a", "button", "summary"):
                return SideEffectClass.LOW_RISK_UI_STATE, "Safe UI state expansion or pagination control", True

        # Ambiguous / Unknown -> Fail Closed
        return SideEffectClass.UNKNOWN, f"Ambiguous element semantics for '{element.element_id}'", False


browser_action_policy = BrowserActionPolicy()
