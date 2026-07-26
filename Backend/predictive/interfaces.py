from typing import Protocol, List, Optional, Dict, Any
from unified_context.models import CognitiveContext
from predictive.models import (
    IntentPrediction,
    WorkflowPrediction,
    PredictionCandidate,
    GoalPrediction,
    Suggestion,
    PredictionResult,
)


class IIntentForecaster(Protocol):
    def forecast_intents(self, context: CognitiveContext) -> List[IntentPrediction]:
        ...


class IWorkflowAnticipator(Protocol):
    def anticipate_workflows(
        self, intents: List[IntentPrediction], context: CognitiveContext
    ) -> List[WorkflowPrediction]:
        ...


class IConfidenceRanker(Protocol):
    def score_and_rank(
        self, candidates: List[PredictionCandidate], context: CognitiveContext
    ) -> List[GoalPrediction]:
        ...


class IProactiveSuggester(Protocol):
    def generate_suggestions(
        self, predictions: List[GoalPrediction], min_threshold: float = 0.85
    ) -> List[Suggestion]:
        ...


class IPredictiveGoalEngine(Protocol):
    async def predict(self, context: CognitiveContext) -> PredictionResult:
        ...
