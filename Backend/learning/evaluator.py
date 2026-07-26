import time
from typing import Optional, Dict, Any
from learning.models import LearningFeedback, RewardSignal
from tools.telemetry import log_structured, backend_log


class OutcomeEvaluator:
    """
    Computes a normalized reward signal R in range [-1.0, +1.0] from execution feedback.
    Evaluates success, duration, retries, user rating, policy violations, reflection reports,
    and failure severity.
    """

    def __init__(
        self,
        base_success_reward: float = 0.60,
        base_failure_penalty: float = -0.60,
        retry_penalty_per_step: float = 0.10,
        violation_penalty_per_item: float = 0.20,
    ):
        self.base_success_reward = base_success_reward
        self.base_failure_penalty = base_failure_penalty
        self.retry_penalty_per_step = retry_penalty_per_step
        self.violation_penalty_per_item = violation_penalty_per_item

    def evaluate_outcome(self, feedback: LearningFeedback) -> RewardSignal:
        try:
            # 1. Base score
            if feedback.success:
                base_score = self.base_success_reward
            else:
                base_score = self.base_failure_penalty

            # 2. Duration penalty / bonus
            duration_penalty = 0.0
            if feedback.duration_sec > 15.0:
                duration_penalty = min(0.30, (feedback.duration_sec - 15.0) * 0.01)
            elif feedback.success and feedback.duration_sec < 2.0:
                # Speed bonus
                base_score += 0.05

            # 3. Retry penalty
            retry_penalty = min(0.40, feedback.retry_count * self.retry_penalty_per_step)

            # 4. User rating boost
            rating_boost = 0.0
            if feedback.user_rating is not None:
                rating_boost = max(-0.40, min(0.40, feedback.user_rating * 0.40))

            # 5. Policy violation penalty
            violation_penalty = min(0.50, len(feedback.policy_violations) * self.violation_penalty_per_item)

            # 6. Reflection score adjustment
            reflection_score = 0.0
            if feedback.reflection_report and isinstance(feedback.reflection_report, dict):
                conf_adj = feedback.reflection_report.get("confidence_adjustment", 0.0)
                if isinstance(conf_adj, (int, float)):
                    reflection_score = max(-0.30, min(0.30, float(conf_adj)))

            # 7. Severity penalty (applied on failure)
            severity_penalty = 0.0
            if not feedback.success:
                severity_penalty = min(0.40, feedback.failure_severity * 0.40)

            # 8. Compute final raw reward and clamp [-1.0, +1.0]
            raw_reward = (
                base_score
                - duration_penalty
                - retry_penalty
                + rating_boost
                - violation_penalty
                + reflection_score
                - severity_penalty
            )

            final_reward = max(-1.0, min(1.0, round(raw_reward, 4)))

            reward_signal = RewardSignal(
                execution_id=feedback.execution_id,
                goal_id=feedback.goal_id,
                strategy_id=feedback.strategy_id,
                base_score=round(base_score, 4),
                duration_penalty=round(duration_penalty, 4),
                retry_penalty=round(retry_penalty, 4),
                rating_boost=round(rating_boost, 4),
                violation_penalty=round(violation_penalty, 4),
                reflection_score=round(reflection_score, 4),
                severity_penalty=round(severity_penalty, 4),
                final_reward=final_reward,
                timestamp=time.time(),
            )

            log_structured(
                backend_log,
                "INFO",
                f"[OutcomeEvaluator] Evaluated reward for strategy '{feedback.strategy_id}': final_reward={final_reward}",
            )
            return reward_signal

        except Exception as e:
            log_structured(backend_log, "ERROR", f"[OutcomeEvaluator] Error evaluating outcome: {str(e)}")
            # Safe fallback reward signal
            fallback_score = 0.5 if feedback.success else -0.5
            return RewardSignal(
                execution_id=feedback.execution_id,
                goal_id=feedback.goal_id,
                strategy_id=feedback.strategy_id,
                base_score=fallback_score,
                final_reward=fallback_score,
                timestamp=time.time(),
            )
