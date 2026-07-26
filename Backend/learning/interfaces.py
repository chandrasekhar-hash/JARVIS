from typing import Protocol, List, Optional, Dict, Any
from learning.models import (
    LearningFeedback,
    RewardSignal,
    CalibrationResult,
    StrategyLearningRecord,
    LearningMetrics,
    BehaviourRecommendation,
    LearningPipelineResult,
)


class IOutcomeEvaluator(Protocol):
    def evaluate_outcome(self, feedback: LearningFeedback) -> RewardSignal:
        """Computes a normalized reward signal in range [-1.0, +1.0] from execution feedback."""
        ...


class IConfidenceCalibrator(Protocol):
    def calibrate(
        self,
        feedback: LearningFeedback,
        reward: RewardSignal,
        prior_confidence: float,
        historical_rewards: List[float],
    ) -> CalibrationResult:
        """Calibrates strategy confidence using moving averages, historical weighting, and thresholds."""
        ...


class IStrategyOptimizer(Protocol):
    def optimize_strategy(
        self,
        record: StrategyLearningRecord,
        calibration: CalibrationResult,
    ) -> StrategyLearningRecord:
        """Optimizes strategy ranking weights, reuse scores, and historical success scores."""
        ...


class IBehavioralAdapter(Protocol):
    def recommend_behavior_adjustments(
        self,
        strategy_records: List[StrategyLearningRecord],
        metrics: LearningMetrics,
    ) -> List[BehaviourRecommendation]:
        """Generates system behavioral tuning recommendations based on overall performance trends."""
        ...


class ILearningEngine(Protocol):
    async def process_feedback(self, feedback: LearningFeedback) -> LearningPipelineResult:
        """Executes full 9-step learning pipeline and returns structured calibration result."""
        ...

    def get_strategy_record(self, strategy_id: str) -> Optional[StrategyLearningRecord]:
        """Retrieves current learning record for a given strategy ID."""
        ...

    def get_metrics(self) -> LearningMetrics:
        """Returns aggregated learning engine metrics."""
        ...
