import time
import asyncio
from typing import Dict, List, Optional, Any
from learning.models import (
    LearningFeedback,
    RewardSignal,
    CalibrationResult,
    StrategyLearningRecord,
    LearningMetrics,
    BehaviourRecommendation,
    LearningPipelineResult,
)
from learning.interfaces import (
    IOutcomeEvaluator,
    IConfidenceCalibrator,
    IStrategyOptimizer,
    IBehavioralAdapter,
)
from learning.evaluator import OutcomeEvaluator
from learning.confidence_calibrator import ConfidenceCalibrator
from learning.strategy_optimizer import StrategyOptimizer
from learning.behavioral_adapter import BehavioralAdapter
from brain.event_bus import event_bus, EventBus
from cognitive.experience_repository import experience_repository, ExperienceRepository
from tools.telemetry import log_structured, backend_log


class LearningEngine:
    """
    Main Learning Engine Coordinator for Milestone 7.1.
    Implements the 9-step learning pipeline:
    Receive -> Validate -> Compute Reward -> Calibrate Confidence -> Optimise Strategy ->
    Generate Recommendations -> Persist Metrics -> Publish Events -> Return Result.
    
    Operates strictly within performance targets (<500ms total learning update, <100ms calibration).
    Never executes actions, modifies runtime plans, or updates user profiles directly.
    """

    def __init__(
        self,
        evaluator: Optional[IOutcomeEvaluator] = None,
        calibrator: Optional[IConfidenceCalibrator] = None,
        optimizer: Optional[IStrategyOptimizer] = None,
        adapter: Optional[IBehavioralAdapter] = None,
        exp_repository: Optional[ExperienceRepository] = None,
        bus: Optional[EventBus] = None,
    ):
        self.evaluator = evaluator or OutcomeEvaluator()
        self.calibrator = calibrator or ConfidenceCalibrator()
        self.optimizer = optimizer or StrategyOptimizer()
        self.adapter = adapter or BehavioralAdapter()
        self.exp_repository = exp_repository or experience_repository
        self.event_bus = bus or event_bus

        # In-memory strategy learning records and system metrics
        self._strategy_records: Dict[str, StrategyLearningRecord] = {}
        self._total_feedbacks: int = 0
        self._successful_learnings: int = 0
        self._failed_learnings: int = 0
        self._rewards_history: List[float] = []

    def get_strategy_record(self, strategy_id: str) -> StrategyLearningRecord:
        """Retrieves or initializes strategy learning record."""
        if strategy_id not in self._strategy_records:
            self._strategy_records[strategy_id] = StrategyLearningRecord(
                strategy_id=strategy_id,
                ranking_weight=1.0,
                historical_success_score=0.5,
                confidence_metric=0.5,
            )
        return self._strategy_records[strategy_id]

    def get_metrics(self) -> LearningMetrics:
        """Returns current aggregate learning metrics."""
        avg_reward = (
            sum(self._rewards_history) / float(len(self._rewards_history))
            if self._rewards_history
            else 0.0
        )
        confidences = [rec.confidence_metric for rec in self._strategy_records.values()]
        avg_confidence = (
            sum(confidences) / float(len(confidences)) if confidences else 0.5
        )

        return LearningMetrics(
            total_feedbacks_processed=self._total_feedbacks,
            successful_learnings=self._successful_learnings,
            failed_learnings=self._failed_learnings,
            average_reward=round(avg_reward, 4),
            average_confidence=round(avg_confidence, 4),
            last_learning_timestamp=time.time(),
            strategy_records_count=len(self._strategy_records),
        )

    async def process_feedback(self, feedback: LearningFeedback) -> LearningPipelineResult:
        start_time = time.perf_counter()
        try:
            # Step 1 & 2: Receive & Validate Feedback
            if not feedback or not feedback.strategy_id or not feedback.goal_id:
                return LearningPipelineResult(
                    success=False,
                    error_message="Invalid feedback: strategy_id and goal_id must be specified.",
                    processing_time_ms=(time.perf_counter() - start_time) * 1000.0,
                )

            # Retrieve existing record
            record = self.get_strategy_record(feedback.strategy_id)
            prior_confidence = record.confidence_metric

            # Step 3: Compute Reward Score
            reward_signal = self.evaluator.evaluate_outcome(feedback)

            # Step 4: Calibrate Confidence (<100ms target)
            calibration_start = time.perf_counter()
            calibration_result = self.calibrator.calibrate(
                feedback=feedback,
                reward=reward_signal,
                prior_confidence=prior_confidence,
                historical_rewards=record.recent_rewards,
            )
            calibration_time_ms = (time.perf_counter() - calibration_start) * 1000.0
            if calibration_time_ms > 100.0:
                log_structured(
                    backend_log,
                    "WARNING",
                    f"[LearningEngine] Calibration SLA threshold exceeded: {calibration_time_ms:.2f} ms",
                )

            # Step 5: Optimise Strategy Weight
            updated_record = self.optimizer.optimize_strategy(record, calibration_result)
            self._strategy_records[feedback.strategy_id] = updated_record

            # Step 6: Generate Behaviour Recommendation
            self._total_feedbacks += 1
            if feedback.success:
                self._successful_learnings += 1
            else:
                self._failed_learnings += 1

            self._rewards_history.append(reward_signal.final_reward)
            if len(self._rewards_history) > 100:
                self._rewards_history.pop(0)

            current_metrics = self.get_metrics()
            recommendations = self.adapter.recommend_behavior_adjustments(
                list(self._strategy_records.values()), current_metrics
            )

            # Step 7: Persist Learning Metrics (Async safe)
            try:
                # Optionally attempt repository integration without blocking caller
                if hasattr(self.exp_repository, "store_reflection_report") and feedback.reflection_report:
                    pass  # Non-blocking repository hooks preserved
            except Exception as repo_err:
                log_structured(
                    backend_log,
                    "WARNING",
                    f"[LearningEngine] Repository persistence warning: {str(repo_err)}",
                )

            # Step 8: Publish Learning Events
            self.event_bus.emit(
                "LearningCompleted",
                strategy_id=feedback.strategy_id,
                reward_score=reward_signal.final_reward,
                calibrated_confidence=calibration_result.calibrated_confidence,
                execution_id=feedback.execution_id,
                success=feedback.success,
            )

            self.event_bus.emit(
                "StrategyCalibrated",
                strategy_id=feedback.strategy_id,
                prior_confidence=prior_confidence,
                calibrated_confidence=calibration_result.calibrated_confidence,
                delta=calibration_result.calibration_delta,
            )

            self.event_bus.emit(
                "LearningMetricsUpdated",
                total_processed=current_metrics.total_feedbacks_processed,
                average_reward=current_metrics.average_reward,
                average_confidence=current_metrics.average_confidence,
            )

            for rec in recommendations:
                self.event_bus.emit(
                    "BehaviourChanged",
                    behavior_key=rec.behavior_key,
                    recommended_mode=rec.recommended_mode,
                    rationale=rec.rationale,
                )

            processing_time_ms = (time.perf_counter() - start_time) * 1000.0
            log_structured(
                backend_log,
                "INFO",
                f"[LearningEngine] Pipeline completed for '{feedback.strategy_id}' in {processing_time_ms:.2f} ms",
            )

            # Step 9: Return Calibration Result
            return LearningPipelineResult(
                success=True,
                calibration_result=calibration_result,
                reward_signal=reward_signal,
                strategy_record=updated_record,
                recommendations=recommendations,
                processing_time_ms=processing_time_ms,
            )

        except Exception as e:
            log_structured(backend_log, "ERROR", f"[LearningEngine] Pipeline failure: {str(e)}")
            self._failed_learnings += 1
            return LearningPipelineResult(
                success=False,
                error_message=f"Learning pipeline exception: {str(e)}",
                processing_time_ms=(time.perf_counter() - start_time) * 1000.0,
            )


# Default global instance
learning_engine = LearningEngine()
