"""
J.A.R.V.I.S. Intelligence I2.2 V7 — Interactive Browser & Dynamic Web Intelligence.
Purely additive subpackage for dynamic browser rendering, static-first escalation,
network request interception, read-only action safety, side-effect classification,
element reference fingerprinting, and dynamic content extraction.
"""
from intelligence.web.browser.models import (
    BrowserExecutionStatus,
    BrowserEscalationReason,
    BrowserActionType,
    SideEffectClass,
    LinkRejectionReason,
    ElementRef,
    BrowserPageObservation,
    BrowserActionPlan,
    BrowserEvidenceItem,
    BrowserWebRequest,
    BrowserWebResponse,
    BrowserConfig,
)
from intelligence.web.browser.browser_service import web_browser_service, BrowserWebService

__all__ = [
    "BrowserExecutionStatus",
    "BrowserEscalationReason",
    "BrowserActionType",
    "SideEffectClass",
    "LinkRejectionReason",
    "ElementRef",
    "BrowserPageObservation",
    "BrowserActionPlan",
    "BrowserEvidenceItem",
    "BrowserWebRequest",
    "BrowserWebResponse",
    "BrowserConfig",
    "web_browser_service",
    "BrowserWebService",
]
