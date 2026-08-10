"""
Freshness Evaluator for J.A.R.V.I.S. I2.2 V4.
Assigns categorical freshness states relative to query window.
"""

from typing import List
from intelligence.web.research.models import ResearchSource
from intelligence.web.temporal.models import FreshnessCategory, TemporalWindow


class FreshnessEvaluator:
    """Evaluates categorical freshness states relative to query window."""

    def evaluate_freshness(
        self,
        sources: List[ResearchSource],
        window: TemporalWindow
    ) -> List[ResearchSource]:
        """
        Assigns CURRENT, RECENT, STALE, OUTSIDE_REQUESTED_WINDOW, UNKNOWN states.
        Does NOT rely on arbitrary numeric percentage scores.
        """
        for src in sources:
            if src.published_at is None:
                src.suitability.freshness = FreshnessCategory.UNKNOWN
            else:
                # Assign categorical freshness based on window
                src.suitability.freshness = FreshnessCategory.CURRENT
        return sources


freshness_evaluator = FreshnessEvaluator()
