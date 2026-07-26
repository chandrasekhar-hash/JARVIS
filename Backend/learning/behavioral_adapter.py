import time
from typing import List, Dict, Any
from learning.models import StrategyLearningRecord, LearningMetrics, BehaviourRecommendation
from tools.telemetry import log_structured, backend_log


class BehavioralAdapter:
    """
    Analyzes strategy performance records and learning metrics to produce system behavioral
    tuning recommendations.
    Does NOT modify runtime behavior directly.
    """

    def __init__(self, confidence_low_threshold: float = 0.45, confidence_high_threshold: float = 0.85):
        self.confidence_low_threshold = confidence_low_threshold
        self.confidence_high_threshold = confidence_high_threshold

    def recommend_behavior_adjustments(
        self,
        strategy_records: List[StrategyLearningRecord],
        metrics: LearningMetrics,
    ) -> List[BehaviourRecommendation]:
        recommendations: List[BehaviourRecommendation] = []
        try:
            if not strategy_records:
                return recommendations

            avg_confidence = metrics.average_confidence
            total_processed = metrics.total_feedbacks_processed

            # 1. Evaluate overall confidence levels
            if avg_confidence < self.confidence_low_threshold and total_processed >= 3:
                recommendations.append(
                    BehaviourRecommendation(
                        behavior_key="intent_routing_mode",
                        current_mode="balanced",
                        recommended_mode="conservative_verification",
                        rationale=f"System average confidence ({avg_confidence:.2f}) dropped below threshold ({self.confidence_low_threshold:.2f}). Recommending conservative verification mode.",
                        confidence_basis=round(1.0 - avg_confidence, 4),
                        suggested_params={"max_iterations": 3, "require_confirmation": True},
                        timestamp=time.time(),
                    )
                )
            elif avg_confidence > self.confidence_high_threshold and total_processed >= 5:
                recommendations.append(
                    BehaviourRecommendation(
                        behavior_key="intent_routing_mode",
                        current_mode="balanced",
                        recommended_mode="fast_path_optimization",
                        rationale=f"System average confidence ({avg_confidence:.2f}) exceeds high threshold ({self.confidence_high_threshold:.2f}). Recommending fast-path optimization.",
                        confidence_basis=round(avg_confidence, 4),
                        suggested_params={"bypass_low_risk_reflection": True},
                        timestamp=time.time(),
                    )
                )

            # 2. Evaluate strategy-specific failure rates
            for rec in strategy_records:
                if rec.total_trials >= 5 and rec.historical_success_score < 0.35:
                    recommendations.append(
                        BehaviourRecommendation(
                            behavior_key=f"strategy_policy_{rec.strategy_id}",
                            current_mode="active",
                            recommended_mode="fallback_probing",
                            rationale=f"Strategy '{rec.strategy_id}' exhibits low historical success rate ({rec.historical_success_score:.2f}). Recommending fallback probing mode.",
                            confidence_basis=round(1.0 - rec.historical_success_score, 4),
                            suggested_params={"strategy_id": rec.strategy_id, "demotion_weight": 0.2},
                            timestamp=time.time(),
                        )
                    )

            log_structured(
                backend_log,
                "INFO",
                f"[BehavioralAdapter] Generated {len(recommendations)} behavior recommendations",
            )
            return recommendations

        except Exception as e:
            log_structured(backend_log, "ERROR", f"[BehavioralAdapter] Error generating recommendations: {str(e)}")
            return recommendations
