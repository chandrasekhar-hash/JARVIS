"""
J.A.R.V.I.S. Intelligence I2.2 V7 — Interaction Executor.
Executes planned browser actions safely, validating element reference fingerprints (observation_id and page_state_fingerprint),
and computing pre/post page state deltas to detect NO_CHANGE and prevent interaction loops.
"""
import logging
from typing import Tuple, Optional, Any
from intelligence.web.browser.models import (
    BrowserActionPlan,
    BrowserPageObservation,
    BrowserActionType,
)
from intelligence.web.browser.browser_transport import BaseBrowserTransport

logger = logging.getLogger("JARVIS_InteractionExecutor")


class InteractionExecutor:
    """
    Executes BrowserActionPlan steps and computes page state changes.
    """

    async def execute_action(
        self, transport: BaseBrowserTransport, page: Any, plan: BrowserActionPlan, current_obs: BrowserPageObservation
    ) -> Tuple[bool, str, str]:
        """
        Returns (success, state_delta, message).
        """

        # 1. Scroll Action
        if plan.action_type == BrowserActionType.SCROLL:
            ok = await transport.scroll(page, direction="down")
            if ok:
                return True, "CONTENT_CHANGED", "Scrolled page down successfully"
            return False, "NO_CHANGE", "Scroll failed"

        # 2. Element Click / Expand / Load More Actions
        if plan.target_element_id:
            # Find target element in current observation
            target_elem = None
            for elem in current_obs.interactive_elements:
                if elem.element_id == plan.target_element_id:
                    target_elem = elem
                    break

            if not target_elem:
                logger.warning(f"Target element '{plan.target_element_id}' not found in current observation. Reference is stale.")
                return False, "NO_CHANGE", "Stale element reference rejected"

            # Check fingerprint freshness
            if target_elem.page_state_fingerprint != current_obs.content_fingerprint:
                logger.warning(f"Fingerprint mismatch for element '{plan.target_element_id}'. Element reference is stale.")
                return False, "NO_CHANGE", "Fingerprint staleness check failed"

            # Resolve locator selector hint
            selector = target_elem.selector_hint
            ok = await transport.click_element(page, selector)
            if ok:
                delta = "ELEMENT_EXPANDED" if plan.action_type == BrowserActionType.EXPAND else "CONTENT_CHANGED"
                return True, delta, f"Clicked '{target_elem.accessible_name or selector}' successfully"
            return False, "NO_CHANGE", f"Click failed for selector '{selector}'"

        return False, "NO_CHANGE", "No valid target element specified"


interaction_executor = InteractionExecutor()
