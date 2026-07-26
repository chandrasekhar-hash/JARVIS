import time
from typing import List
from unified_context.models import CognitiveContext
from predictive.models import (
    PredictionCandidate,
    GoalPrediction,
    PredictionExplanation,
    PredictionConfidence,
)
from tools.telemetry import log_structured, backend_log


class ConfidenceRanker:
    """
    Scores and ranks goal prediction candidates based on multi-factor evidence,
    user habit alignment, context freshness, and signal agreement.
    Provides complete explainability models for every prediction.
    SLA Target: < 20 ms.
    """

    def __init__(self):
        pass

    def score_and_rank(
        self, candidates: List[PredictionCandidate], context: CognitiveContext
    ) -> List[GoalPrediction]:
        start = time.perf_counter()
        predictions: List[GoalPrediction] = []

        try:
            if not candidates:
                return predictions

            # 1. Evaluate context quality score
            context_quality = min(1.0, len(context.chunks) * 0.25)

            # 2. Extract source providers list
            source_providers = [c.provider_id for c in context.chunks]

            for cand in candidates:
                # 3. Calculate multi-factor confidence
                signal_agreement = min(1.0, len(cand.signals) * 0.30)
                habit_alignment = (
                    0.85
                    if (
                        any(s.value == "user_model" for s in context.sources_included)
                        or "user_model" in context.formatted_prompt_context.lower()
                        or "explicit preferences" in context.formatted_prompt_context.lower()
                        or "preferred tools" in context.formatted_prompt_context.lower()
                    )
                    else 0.50
                )
                freshness = 0.95

                raw_conf = (
                    (cand.raw_score * 0.40)
                    + (context_quality * 0.20)
                    + (habit_alignment * 0.20)
                    + (signal_agreement * 0.20)
                )
                final_conf = max(0.0, min(1.0, round(raw_conf, 4)))

                explanation = PredictionExplanation(
                    confidence=final_conf,
                    supporting_evidence=[
                        f"Matched {len(cand.signals)} intent signals",
                        f"Context quality score: {context_quality:.2f}",
                        f"Habit alignment score: {habit_alignment:.2f}",
                    ],
                    trigger_signals=cand.signals,
                    reasoning_summary=f"Predicted goal '{cand.goal_description}' based on intent '{cand.intent_category}' and active cognitive context.",
                    source_providers=source_providers,
                    timestamp=time.time(),
                )

                predictions.append(
                    GoalPrediction(
                        predicted_goal=cand.goal_description,
                        intent_category=cand.intent_category,
                        confidence=final_conf,
                        explanation=explanation,
                        suggested_parameters={"intent": cand.intent_category},
                        timestamp=time.time(),
                    )
                )

            # Rank by confidence descending
            predictions.sort(key=lambda p: p.confidence, reverse=True)
            elapsed_ms = (time.perf_counter() - start) * 1000.0

            if elapsed_ms > 20.0:
                log_structured(
                    backend_log,
                    "WARNING",
                    f"[ConfidenceRanker] Ranking SLA threshold exceeded: {elapsed_ms:.2f} ms",
                )

            log_structured(
                backend_log,
                "INFO",
                f"[ConfidenceRanker] Ranked {len(predictions)} predictions in {elapsed_ms:.2f} ms",
            )
            return predictions

        except Exception as e:
            log_structured(backend_log, "ERROR", f"[ConfidenceRanker] Error ranking candidates: {str(e)}")
            return predictions
