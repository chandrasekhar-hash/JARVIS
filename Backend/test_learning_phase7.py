import os
import sys
import time
import asyncio
import unittest

# Ensure Backend directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from learning.models import (
    LearningFeedback,
    RewardSignal,
    CalibrationResult,
    StrategyLearningRecord,
    LearningMetrics,
    BehaviourRecommendation,
)
from learning.evaluator import OutcomeEvaluator
from learning.confidence_calibrator import ConfidenceCalibrator
from learning.strategy_optimizer import StrategyOptimizer
from learning.behavioral_adapter import BehavioralAdapter
from learning.engine import LearningEngine
from brain.event_bus import EventBus


class TestLearningEnginePhase7(unittest.IsolatedAsyncioTestCase):

    async def test_reward_calculation_success_and_penalties(self):
        evaluator = OutcomeEvaluator()

        # Success feedback
        feedback_success = LearningFeedback(
            goal_id="goal_1",
            strategy_id="strat_direct",
            success=True,
            duration_sec=1.5,
            retry_count=0,
            user_rating=1.0,
        )
        reward_success = evaluator.evaluate_outcome(feedback_success)
        self.assertGreater(reward_success.final_reward, 0.6)
        self.assertGreater(reward_success.rating_boost, 0.0)

        # Failure feedback with retries and policy violations
        feedback_failure = LearningFeedback(
            goal_id="goal_2",
            strategy_id="strat_decomp",
            success=False,
            duration_sec=30.0,
            retry_count=3,
            policy_violations=["LOW_CONFIDENCE", "PATH_RESTRICTION"],
            failure_severity=0.8,
        )
        reward_failure = evaluator.evaluate_outcome(feedback_failure)
        self.assertLess(reward_failure.final_reward, -0.5)
        self.assertGreater(reward_failure.retry_penalty, 0.0)
        self.assertGreater(reward_failure.violation_penalty, 0.0)
        self.assertGreater(reward_failure.severity_penalty, 0.0)

        # Clamping test
        self.assertTrue(-1.0 <= reward_success.final_reward <= 1.0)
        self.assertTrue(-1.0 <= reward_failure.final_reward <= 1.0)

    async def test_confidence_calibration(self):
        calibrator = ConfidenceCalibrator(min_samples_threshold=3)
        evaluator = OutcomeEvaluator()

        feedback = LearningFeedback(
            goal_id="goal_test",
            strategy_id="strat_1",
            success=True,
            duration_sec=1.0,
        )
        reward = evaluator.evaluate_outcome(feedback)

        # Initial calibration (low sample count -> prior dominates)
        res1 = calibrator.calibrate(feedback, reward, prior_confidence=0.50, historical_rewards=[])
        self.assertEqual(res1.prior_confidence, 0.50)
        self.assertTrue(0.0 <= res1.calibrated_confidence <= 1.0)
        self.assertEqual(res1.samples_count, 1)

        # Boost test on repeated success
        res2 = calibrator.calibrate(feedback, reward, prior_confidence=res1.calibrated_confidence, historical_rewards=[0.6, 0.7, 0.8])
        self.assertGreaterEqual(res2.boost_applied, 0.0)
        self.assertGreaterEqual(res2.calibrated_confidence, res1.calibrated_confidence)

        # Decay test on failure
        fail_feedback = LearningFeedback(goal_id="g_fail", strategy_id="strat_1", success=False)
        fail_reward = evaluator.evaluate_outcome(fail_feedback)
        res_decay = calibrator.calibrate(fail_feedback, fail_reward, prior_confidence=0.80, historical_rewards=[0.7, 0.6])
        self.assertGreater(res_decay.decay_applied, 0.0)
        self.assertLess(res_decay.calibrated_confidence, 0.80)

    async def test_strategy_optimizer(self):
        optimizer = StrategyOptimizer()
        record = StrategyLearningRecord(strategy_id="strat_opt", ranking_weight=1.0, confidence_metric=0.5)

        calib_success = CalibrationResult(
            strategy_id="strat_opt",
            prior_confidence=0.5,
            calibrated_confidence=0.8,
            calibration_delta=0.3,
            reward_score=0.7,
            samples_count=5,
            moving_average=0.7,
        )

        opt_record = optimizer.optimize_strategy(record, calib_success)
        self.assertEqual(opt_record.total_trials, 1)
        self.assertEqual(opt_record.success_count, 1)
        self.assertEqual(opt_record.historical_success_score, 1.0)
        self.assertEqual(opt_record.confidence_metric, 0.8)
        self.assertGreater(opt_record.ranking_weight, 1.0)

    async def test_behavioral_adapter(self):
        adapter = BehavioralAdapter(confidence_low_threshold=0.45)
        records = [
            StrategyLearningRecord(strategy_id="strat_low", total_trials=5, success_count=1, historical_success_score=0.20)
        ]
        metrics = LearningMetrics(
            total_feedbacks_processed=5,
            successful_learnings=1,
            failed_learnings=4,
            average_reward=-0.3,
            average_confidence=0.30,
        )

        recs = adapter.recommend_behavior_adjustments(records, metrics)
        self.assertGreaterEqual(len(recs), 1)
        modes = [r.recommended_mode for r in recs]
        self.assertTrue("conservative_verification" in modes or "fallback_probing" in modes)

    async def test_learning_engine_full_pipeline_and_events(self):
        custom_bus = EventBus()
        emitted_events = []

        def event_listener(evt):
            emitted_events.append(evt.name)

        custom_bus.subscribe("LearningCompleted", event_listener)
        custom_bus.subscribe("StrategyCalibrated", event_listener)
        custom_bus.subscribe("LearningMetricsUpdated", event_listener)
        custom_bus.subscribe("BehaviourChanged", event_listener)

        engine = LearningEngine(bus=custom_bus)

        feedback = LearningFeedback(
            goal_id="g_pipeline",
            strategy_id="strat_pipe",
            success=True,
            duration_sec=2.0,
            user_rating=0.8,
        )

        result = await engine.process_feedback(feedback)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.calibration_result)
        self.assertIsNotNone(result.reward_signal)
        self.assertLess(result.processing_time_ms, 500.0)  # SLA < 500ms target

        await asyncio.sleep(0.05)
        self.assertIn("LearningCompleted", emitted_events)
        self.assertIn("StrategyCalibrated", emitted_events)
        self.assertIn("LearningMetricsUpdated", emitted_events)

    async def test_learning_engine_error_handling(self):
        engine = LearningEngine()

        # Invalid empty strategy feedback
        invalid_feedback = LearningFeedback(goal_id="", strategy_id="", success=True)
        res_invalid = await engine.process_feedback(invalid_feedback)
        self.assertFalse(res_invalid.success)
        self.assertIn("Invalid feedback", res_invalid.error_message)

        # Metrics recovery
        metrics = engine.get_metrics()
        self.assertGreaterEqual(metrics.total_feedbacks_processed, 0)

    async def test_performance_sla(self):
        engine = LearningEngine()
        feedback = LearningFeedback(
            goal_id="g_perf",
            strategy_id="strat_perf",
            success=True,
            duration_sec=0.5,
        )

        start = time.perf_counter()
        res = await engine.process_feedback(feedback)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        self.assertTrue(res.success)
        self.assertLess(elapsed_ms, 500.0)  # Learning update < 500ms


if __name__ == "__main__":
    unittest.main()
