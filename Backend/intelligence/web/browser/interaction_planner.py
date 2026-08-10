"""
J.A.R.V.I.S. Intelligence I2.2 V7 — Interaction Planner.
Plans safe, query-relevant browser actions based on Page Observations.
Enforces hard server bound MAX_BROWSER_ACTIONS = 12.
"""
import re
import logging
from typing import List, Optional
from intelligence.web.browser.models import (
    BrowserPageObservation,
    BrowserActionPlan,
    BrowserActionType,
    SideEffectClass,
    BrowserConfig,
)
from intelligence.web.browser.browser_policy import browser_action_policy

logger = logging.getLogger("JARVIS_InteractionPlanner")


class InteractionPlanner:
    """
    Plans interaction steps deterministically based on user query and page observation.
    """

    def plan_next_actions(
        self, query: str, obs: BrowserPageObservation, executed_count: int
    ) -> List[BrowserActionPlan]:
        plans: List[BrowserActionPlan] = []
        if executed_count >= BrowserConfig.MAX_BROWSER_ACTIONS:
            logger.info("MAX_BROWSER_ACTIONS limit reached. No further actions planned.")
            return plans

        query_lower = query.lower()
        query_tokens = set(re.findall(r"\b\w{3,}\b", query_lower))

        # Check interactive elements on page
        for elem in obs.interactive_elements:
            if len(plans) >= 2:  # Plan up to 2 candidate steps per observation round
                break

            name_lower = elem.accessible_name.lower()
            text_lower = elem.visible_text.lower()

            # Check if element matches expansion / accordion / tab / show more / load more / next page keywords
            is_expand_intent = any(k in query_lower for k in ("expand", "accordion", "more", "details", "tab", "compatibility", "specs"))
            is_elem_expand = any(k in name_lower or k in text_lower for k in ("show more", "expand", "details", "read more", "compatibility", "specifications", "next", "load more"))

            if is_expand_intent or is_elem_expand:
                action_type = BrowserActionType.EXPAND
                if "next" in name_lower or "load more" in name_lower:
                    action_type = BrowserActionType.LOAD_MORE

                # Classify safety via browser_action_policy
                side_effect, reason, is_allowed = browser_action_policy.classify_action_safety(action_type, elem)

                if is_allowed:
                    plan = BrowserActionPlan(
                        action_id=f"act_{executed_count + len(plans) + 1}",
                        action_type=action_type,
                        target_element_id=elem.element_id,
                        reason=reason,
                        side_effect_class=side_effect,
                        safety_status="ALLOWED",
                    )
                    plans.append(plan)

        # Fallback if no specific element matched: add Scroll action if requested
        if not plans and "scroll" in query_lower:
            side_effect, reason, is_allowed = browser_action_policy.classify_action_safety(BrowserActionType.SCROLL)
            plans.append(
                BrowserActionPlan(
                    action_id=f"act_{executed_count + 1}",
                    action_type=BrowserActionType.SCROLL,
                    reason="Scroll page to reveal dynamically loaded content",
                    side_effect_class=SideEffectClass.READ_ONLY,
                    safety_status="ALLOWED",
                )
            )

        return plans


interaction_planner = InteractionPlanner()
