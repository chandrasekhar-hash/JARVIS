import time
from typing import List, Optional
from self_optimization.models import (
    Bottleneck,
    PerformanceTrend,
    OptimisationRecommendation,
    RecommendationPriority,
    OptimisationReport,
)
from brain.event_bus import event_bus, EventBus
from tools.telemetry import log_structured, backend_log


class RecommendationEngine:
    """
    Generates non-intrusive optimization recommendations and comprehensive reports based on system analysis.
    Does NOT execute actions, retrain models, or rewrite configuration files directly.
    SLA Target: Recommendation Generation < 30 ms.
    """

    def __init__(self, bus: Optional[EventBus] = None):
        self.event_bus = bus or event_bus

    def generate_recommendations(
        self, bottlenecks: List[Bottleneck], trends: List[PerformanceTrend]
    ) -> List[OptimisationRecommendation]:
        start = time.perf_counter()
        recommendations: List[OptimisationRecommendation] = []

        try:
            for b in bottlenecks:
                if b.subsystem == "unified_context" and b.bottleneck_type == "high_latency":
                    rec = OptimisationRecommendation(
                        target_subsystem="unified_context",
                        parameter_key="max_unified_context_tokens",
                        current_value=4096,
                        proposed_value=2048,
                        priority=RecommendationPriority.HIGH,
                        rationale="Reduce maximum token budget to speed up state assembly latency under 200 ms SLA.",
                        estimated_improvement="15-25% reduction in context assembly latency",
                        timestamp=time.time(),
                    )
                    recommendations.append(rec)
                elif b.subsystem == "predictive" and b.bottleneck_type == "high_latency":
                    rec = OptimisationRecommendation(
                        target_subsystem="predictive",
                        parameter_key="prediction_confidence_threshold",
                        current_value=0.85,
                        proposed_value=0.80,
                        priority=RecommendationPriority.MEDIUM,
                        rationale="Adjust prediction confidence threshold to optimize candidate filtering speed.",
                        estimated_improvement="10-15% latency reduction in candidate ranking",
                        timestamp=time.time(),
                    )
                    recommendations.append(rec)

            # Standard health maintenance recommendation if no bottlenecks found
            if not recommendations:
                recommendations.append(
                    OptimisationRecommendation(
                        target_subsystem="system",
                        parameter_key="maintenance_status",
                        current_value="optimal",
                        proposed_value="optimal",
                        priority=RecommendationPriority.LOW,
                        rationale="System performance SLAs are satisfying operational targets.",
                        estimated_improvement="Maintain baseline latency performance",
                        timestamp=time.time(),
                    )
                )

            # Sort by priority
            recommendations.sort(key=lambda r: r.priority.value)

            for r in recommendations:
                self.event_bus.emit(
                    "RecommendationGenerated",
                    recommendation_id=r.recommendation_id,
                    target_subsystem=r.target_subsystem,
                    proposed_value=str(r.proposed_value),
                )

            elapsed_ms = (time.perf_counter() - start) * 1000.0
            if elapsed_ms > 30.0:
                log_structured(
                    backend_log,
                    "WARNING",
                    f"[RecommendationEngine] Recommendation SLA threshold exceeded: {elapsed_ms:.2f} ms",
                )

            log_structured(
                backend_log,
                "INFO",
                f"[RecommendationEngine] Generated {len(recommendations)} recommendations in {elapsed_ms:.2f} ms",
            )
            return recommendations

        except Exception as e:
            log_structured(backend_log, "ERROR", f"[RecommendationEngine] Error generating recommendations: {str(e)}")
            return recommendations

    def build_report(
        self,
        trends: List[PerformanceTrend],
        bottlenecks: List[Bottleneck],
        recommendations: List[OptimisationRecommendation],
    ) -> OptimisationReport:
        exec_summary = f"System performance audit completed. Identified {len(bottlenecks)} bottlenecks and generated {len(recommendations)} advisory tuning recommendations."
        tech_report = f"Detailed Analysis:\n- Trends Analyzed: {len(trends)}\n- Bottlenecks Found: {len(bottlenecks)}\n- Recommendations Prepared: {len(recommendations)}"

        report = OptimisationReport(
            executive_summary=exec_summary,
            technical_report=tech_report,
            trends=trends,
            bottlenecks=bottlenecks,
            recommendations=recommendations,
            timestamp=time.time(),
        )

        self.event_bus.emit(
            "OptimisationReportGenerated",
            report_id=report.report_id,
            recommendations_count=len(recommendations),
        )

        return report
