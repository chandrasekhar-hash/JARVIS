import time
from typing import List, Optional
from predictive.models import GoalPrediction, Suggestion
from tools.telemetry import log_structured, backend_log


class ProactiveSuggester:
    """
    Generates non-intrusive proactive suggestions when prediction confidence meets or exceeds
    the required threshold (default 0.85).
    Does NOT execute actions automatically.
    SLA Target: < 20 ms.
    """

    def __init__(self, default_min_threshold: float = 0.85):
        self.default_min_threshold = default_min_threshold

    def generate_suggestions(
        self, predictions: List[GoalPrediction], min_threshold: Optional[float] = None
    ) -> List[Suggestion]:
        start = time.perf_counter()
        suggestions: List[Suggestion] = []
        threshold = min_threshold if min_threshold is not None else self.default_min_threshold

        try:
            for pred in predictions:
                if pred.confidence >= threshold:
                    suggestions.append(
                        Suggestion(
                            title=f"Proactive Suggestion: {pred.intent_category.replace('_', ' ').title()}",
                            recommended_action=f"Would you like J.A.R.V.I.S. to {pred.predicted_goal.lower()}?",
                            confidence=pred.confidence,
                            explanation=pred.explanation.reasoning_summary,
                            timestamp=time.time(),
                        )
                    )

            elapsed_ms = (time.perf_counter() - start) * 1000.0
            if elapsed_ms > 20.0:
                log_structured(
                    backend_log,
                    "WARNING",
                    f"[ProactiveSuggester] Suggestion generation SLA threshold exceeded: {elapsed_ms:.2f} ms",
                )

            log_structured(
                backend_log,
                "INFO",
                f"[ProactiveSuggester] Generated {len(suggestions)} suggestions (Threshold: {threshold}) in {elapsed_ms:.2f} ms",
            )
            return suggestions

        except Exception as e:
            log_structured(backend_log, "ERROR", f"[ProactiveSuggester] Error generating suggestions: {str(e)}")
            return suggestions
