import time
import asyncio
from typing import Optional, List
from unified_context.models import CognitiveContext
from predictive.models import (
    PredictionResult,
    PredictionMetrics,
    GoalPrediction,
    WorkflowPrediction,
    Suggestion,
)
from predictive.interfaces import (
    IIntentForecaster,
    IWorkflowAnticipator,
    IConfidenceRanker,
    IProactiveSuggester,
)
from predictive.intent_forecaster import IntentForecaster
from predictive.workflow_anticipator import WorkflowAnticipator
from predictive.confidence_ranker import ConfidenceRanker
from predictive.proactive_suggester import ProactiveSuggester
from brain.event_bus import event_bus, EventBus
from tools.telemetry import log_structured, backend_log


class PredictiveGoalEngine:
    """
    Main Predictive Goal Engine for Milestone 7.3.
    Consumes ONLY CognitiveContext to forecast future intents, goal sequences,
    workflows, and confidence-gated proactive suggestions.
    SLA Target: Prediction < 100 ms total latency.
    Does NOT execute workflows, modify preferences, optimize strategies, or alter runtime.
    """

    def __init__(
        self,
        forecaster: Optional[IIntentForecaster] = None,
        anticipator: Optional[IWorkflowAnticipator] = None,
        ranker: Optional[IConfidenceRanker] = None,
        suggester: Optional[IProactiveSuggester] = None,
        bus: Optional[EventBus] = None,
        min_suggestion_threshold: float = 0.85,
    ):
        self.forecaster = forecaster or IntentForecaster()
        self.anticipator = anticipator or WorkflowAnticipator()
        self.ranker = ranker or ConfidenceRanker()
        self.suggester = suggester or ProactiveSuggester(default_min_threshold=min_suggestion_threshold)
        self.event_bus = bus or event_bus
        self.min_suggestion_threshold = min_suggestion_threshold

    async def predict(self, context: CognitiveContext) -> PredictionResult:
        start_time = time.perf_counter()
        try:
            # Step 1 & 2 & 3: Receive Context, Extract Signals, Identify Intent
            intents = self.forecaster.forecast_intents(context)

            # Step 4: Generate Candidate Goals
            candidates = self.forecaster.generate_candidates(intents, context)

            # Step 5: Predict Workflow
            workflows = self.anticipator.anticipate_workflows(intents, context)

            # Step 6 & 7: Score Confidence & Rank Predictions (< 20ms SLA)
            ranked_predictions = self.ranker.score_and_rank(candidates, context)

            # Step 8: Generate Suggestions (< 20ms SLA)
            suggestions = self.suggester.generate_suggestions(
                ranked_predictions, min_threshold=self.min_suggestion_threshold
            )

            # Step 9: Publish Events
            for pred in ranked_predictions:
                self.event_bus.emit(
                    "PredictionGenerated",
                    prediction_id=pred.prediction_id,
                    predicted_goal=pred.predicted_goal,
                    confidence=pred.confidence,
                )

                if pred.confidence < 0.50:
                    self.event_bus.emit(
                        "LowConfidencePrediction",
                        prediction_id=pred.prediction_id,
                        confidence=pred.confidence,
                        reason=pred.explanation.reasoning_summary,
                    )

            for wf in workflows:
                self.event_bus.emit(
                    "WorkflowPredicted",
                    workflow_id=wf.workflow_id,
                    predicted_tool_sequence=wf.predicted_tool_sequence,
                    probability=wf.completion_probability,
                )

            for sug in suggestions:
                self.event_bus.emit(
                    "SuggestionGenerated",
                    suggestion_id=sug.suggestion_id,
                    recommended_action=sug.recommended_action,
                    confidence=sug.confidence,
                )

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            metrics = PredictionMetrics(
                total_predictions_made=len(ranked_predictions),
                high_confidence_predictions=len(
                    [p for p in ranked_predictions if p.confidence >= self.min_suggestion_threshold]
                ),
                suggestions_generated=len(suggestions),
                prediction_latency_ms=elapsed_ms,
                timestamp=time.time(),
            )

            if elapsed_ms > 100.0:
                log_structured(
                    backend_log,
                    "WARNING",
                    f"[PredictiveGoalEngine] Prediction SLA threshold exceeded: {elapsed_ms:.2f} ms",
                )

            log_structured(
                backend_log,
                "INFO",
                f"[PredictiveGoalEngine] Generated {len(ranked_predictions)} predictions ({len(suggestions)} suggestions) in {elapsed_ms:.2f} ms",
            )

            # Step 10: Return PredictionResult
            return PredictionResult(
                success=True,
                context_id=context.context_id if context else "",
                goal_predictions=ranked_predictions,
                workflow_predictions=workflows,
                suggestions=suggestions,
                metrics=metrics,
            )

        except Exception as e:
            log_structured(backend_log, "ERROR", f"[PredictiveGoalEngine] Prediction error: {str(e)}")
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return PredictionResult(
                success=False,
                context_id=context.context_id if context else "",
                error_message=f"Prediction exception: {str(e)}",
                metrics=PredictionMetrics(prediction_latency_ms=elapsed_ms),
            )


# Default global instance
predictive_goal_engine = PredictiveGoalEngine()
