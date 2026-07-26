import time
from typing import List, Optional
from learning.models import StrategyLearningRecord, CalibrationResult
from tools.telemetry import log_structured, backend_log


class StrategyOptimizer:
    """
    Optimizes strategy learning records by adjusting ranking weights, historical success scores,
    reuse scores, and confidence metrics without altering runtime execution logic.
    """

    def __init__(self, max_rewards_history: int = 50):
        self.max_rewards_history = max_rewards_history

    def optimize_strategy(
        self,
        record: StrategyLearningRecord,
        calibration: CalibrationResult,
    ) -> StrategyLearningRecord:
        try:
            # 1. Update trial counters
            record.total_trials += 1
            if calibration.reward_score >= 0.0:
                record.success_count += 1
            else:
                record.failure_count += 1

            # 2. Update historical success score
            if record.total_trials > 0:
                record.historical_success_score = round(
                    record.success_count / float(record.total_trials), 4
                )

            # 3. Update recent rewards buffer
            record.recent_rewards.append(calibration.reward_score)
            if len(record.recent_rewards) > self.max_rewards_history:
                record.recent_rewards.pop(0)

            # 4. Update confidence metric
            record.confidence_metric = calibration.calibrated_confidence

            # 5. Update reuse score
            reuse_delta = 0.15 if calibration.reward_score > 0.0 else -0.05
            record.reuse_score = max(0.0, min(10.0, round(record.reuse_score + reuse_delta, 4)))

            # 6. Re-calculate overall strategy ranking weight [0.1, 10.0]
            base_weight = (
                (record.historical_success_score * 3.0)
                + (record.confidence_metric * 4.0)
                + min(3.0, record.reuse_score * 0.3)
            )
            record.ranking_weight = max(0.1, min(10.0, round(base_weight, 4)))
            record.last_updated_at = time.time()

            log_structured(
                backend_log,
                "INFO",
                f"[StrategyOptimizer] Optimized strategy '{record.strategy_id}': weight={record.ranking_weight}, success_rate={record.historical_success_score}",
            )
            return record

        except Exception as e:
            log_structured(backend_log, "ERROR", f"[StrategyOptimizer] Optimization error: {str(e)}")
            record.last_updated_at = time.time()
            return record
