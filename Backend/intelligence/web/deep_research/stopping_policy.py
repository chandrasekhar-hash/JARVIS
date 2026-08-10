"""
Structural Stopping Policy Evaluator for J.A.R.V.I.S. I2.2 V5.
Evaluates research stopping conditions based strictly on structural novelty state and hard server limits.
No arbitrary numeric scores.
"""

from typing import Tuple, List
from intelligence.web.deep_research.models import (
    StoppingReason,
    DeepResearchConfig,
    EvidenceGap
)
from intelligence.web.deep_research.research_state import DeepResearchState


class StoppingPolicy:
    """Evaluates whether to continue research or stop."""

    def evaluate_stopping_condition(
        self,
        state: DeepResearchState,
        config: DeepResearchConfig,
        has_eligible_links: bool,
        has_eligible_queries: bool
    ) -> Tuple[bool, StoppingReason]:
        """
        Determines whether the deep research loop should stop.
        Returns (should_stop: bool, StoppingReason).
        """
        # 1. Budget Exhaustion (Rounds / Pages / Queries)
        if state.completed_rounds >= config.max_rounds:
            return True, StoppingReason.BUDGET_EXHAUSTED

        if len(state.visited_urls) >= config.max_fetched_pages:
            return True, StoppingReason.BUDGET_EXHAUSTED

        if len(state.attempted_queries) >= config.max_search_queries_total:
            return True, StoppingReason.BUDGET_EXHAUSTED

        # 2. Structural NO_NEW_INFORMATION (Round Novelty = 0)
        if state.completed_rounds >= 1 and not state.is_latest_round_novel():
            return True, StoppingReason.NO_NEW_INFORMATION

        # 3. Source Exhaustion (No eligible links and no candidate queries)
        if not has_eligible_links and not has_eligible_queries:
            return True, StoppingReason.SOURCE_EXHAUSTION

        # 4. Sufficient Evidence (Zero unresolved gaps and primary source present)
        unresolved_gaps = [g for g in state.unresolved_gaps if not g.is_resolved]
        primary_sources = [s for s in state.sources if s.suitability.is_primary_source or s.suitability.is_official]
        if not unresolved_gaps and primary_sources and state.completed_rounds >= 1:
            return True, StoppingReason.SUFFICIENT_EVIDENCE

        # Continue research
        return False, StoppingReason.PARTIAL_EVIDENCE


stopping_policy = StoppingPolicy()
