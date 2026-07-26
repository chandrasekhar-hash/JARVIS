import time
import math
from typing import List
from learning.models import LearningFeedback, RewardSignal, CalibrationResult
from tools.telemetry import log_structured, backend_log


class ConfidenceCalibrator:
    """
    Calibrates strategy confidence using exponential moving averages, historical weighting,
    minimum sample thresholds, decay rules, and confidence boosts.
    Outputs CalibrationResult within performance SLA (<100ms).
    """

    def __init__(
        self,
        min_samples_threshold: int = 3,
        alpha: float = 0.25,
        decay_rate: float = 0.05,
        boost_rate: float = 0.08,
    ):
        self.min_samples_threshold = min_samples_threshold
        self.alpha = alpha
        self.decay_rate = decay_rate
        self.boost_rate = boost_rate

    def calibrate(
        self,
        feedback: LearningFeedback,
        reward: RewardSignal,
        prior_confidence: float,
        historical_rewards: List[float],
    ) -> CalibrationResult:
        try:
            prior_conf = max(0.0, min(1.0, prior_confidence))
            all_rewards = list(historical_rewards) + [reward.final_reward]
            samples_count = len(all_rewards)

            # 1. Exponential moving average of rewards
            ema = all_rewards[0]
            for r in all_rewards[1:]:
                ema = (self.alpha * r) + ((1.0 - self.alpha) * ema)

            moving_average = max(-1.0, min(1.0, ema))

            # 2. Convert normalized reward [-1.0, 1.0] to target confidence [0.0, 1.0]
            target_confidence = (moving_average + 1.0) / 2.0

            # 3. Apply sample threshold weighting
            if samples_count < self.min_samples_threshold:
                # Prior confidence dominates when samples are low
                sample_weight = samples_count / float(self.min_samples_threshold)
                base_calibrated = (prior_conf * (1.0 - sample_weight)) + (target_confidence * sample_weight)
            else:
                base_calibrated = (prior_conf * (1.0 - self.alpha)) + (target_confidence * self.alpha)

            # 4. Confidence Decay / Boost calculation
            decay_applied = 0.0
            boost_applied = 0.0

            if reward.final_reward < 0.0 or not feedback.success:
                decay_applied = self.decay_rate * abs(reward.final_reward)
                calibrated = base_calibrated - decay_applied
            elif reward.final_reward > 0.5 and feedback.success:
                boost_applied = self.boost_rate * reward.final_reward
                calibrated = base_calibrated + boost_applied
            else:
                calibrated = base_calibrated

            # Clamp final calibrated confidence to [0.0, 1.0]
            calibrated_confidence = max(0.0, min(1.0, round(calibrated, 4)))
            delta = round(calibrated_confidence - prior_conf, 4)

            result = CalibrationResult(
                strategy_id=feedback.strategy_id,
                prior_confidence=round(prior_conf, 4),
                calibrated_confidence=calibrated_confidence,
                calibration_delta=delta,
                reward_score=reward.final_reward,
                samples_count=samples_count,
                moving_average=round(moving_average, 4),
                decay_applied=round(decay_applied, 4),
                boost_applied=round(boost_applied, 4),
                timestamp=time.time(),
            )

            log_structured(
                backend_log,
                "INFO",
                f"[ConfidenceCalibrator] Calibrated '{feedback.strategy_id}': {prior_conf} -> {calibrated_confidence} (delta={delta})",
            )
            return result

        except Exception as e:
            log_structured(backend_log, "ERROR", f"[ConfidenceCalibrator] Error calibrating confidence: {str(e)}")
            # Safe fallback
            fallback_conf = max(0.0, min(1.0, prior_confidence))
            return CalibrationResult(
                strategy_id=feedback.strategy_id,
                prior_confidence=fallback_conf,
                calibrated_confidence=fallback_conf,
                calibration_delta=0.0,
                reward_score=reward.final_reward,
                samples_count=len(historical_rewards) + 1,
                moving_average=reward.final_reward,
                decay_applied=0.0,
                boost_applied=0.0,
                timestamp=time.time(),
            )
