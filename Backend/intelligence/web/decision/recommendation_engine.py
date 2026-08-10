"""
Explainable Recommendation Engine for J.A.R.V.I.S. I2.2 V11 Decision Intelligence.
"""
import uuid
from typing import Dict, List, Optional
from intelligence.web.decision.models import (
    CandidateEvaluation,
    CandidateStatus,
    DecisionEvidence,
    DecisionRequirement,
    Recommendation,
    RecommendationExplanation,
    RecommendationStatus,
    RecommendationStability,
    Tradeoff,
)


class RecommendationEngine:
    """
    Produces evidence-backed, explainable recommendations with 5-part structured rationale.
    Handles ties explicitly and avoids forcing arbitrary single winners.
    """

    def generate_recommendations(
        self,
        evaluations: List[CandidateEvaluation],
        requirements: List[DecisionRequirement],
        tradeoffs: List[Tradeoff],
        stability: RecommendationStability,
        evidence_registry: Dict[str, DecisionEvidence],
    ) -> List[Recommendation]:
        recommendations: List[Recommendation] = []

        if not evaluations:
            recommendations.append(
                Recommendation(
                    recommendation_id=f"rec_{uuid.uuid4().hex[:8]}",
                    status=RecommendationStatus.NO_RECOMMENDATION,
                    stability=RecommendationStability.UNSTABLE,
                    explanation=RecommendationExplanation(
                        hard_constraints_satisfied=[],
                        preferences_satisfied=[],
                        key_evidence=[],
                        main_tradeoffs=["Insufficient candidate options found in evidence."],
                        why_alternatives_not_selected=["No valid candidate entities were identified."],
                    ),
                )
            )
            return recommendations

        # Filter candidates eligible for primary recommendation (Rule 1: FAILS_HARD_CONSTRAINT excluded)
        eligible_candidates = [ev for ev in evaluations if ev.status != CandidateStatus.FAILS_HARD_CONSTRAINT]

        if not eligible_candidates:
            recommendations.append(
                Recommendation(
                    recommendation_id=f"rec_{uuid.uuid4().hex[:8]}",
                    status=RecommendationStatus.NO_RECOMMENDATION,
                    stability=RecommendationStability.UNSTABLE,
                    explanation=RecommendationExplanation(
                        hard_constraints_satisfied=[],
                        preferences_satisfied=[],
                        key_evidence=[],
                        main_tradeoffs=["All candidates violated one or more hard constraints."],
                        why_alternatives_not_selected=[f"Candidate {c.candidate.name} failed hard constraints." for c in evaluations],
                    ),
                )
            )
            return recommendations

        # Check for explicit TIE between top eligible candidates
        top_status = eligible_candidates[0].status
        tied_top = [ev for ev in eligible_candidates if ev.status == top_status]

        if len(tied_top) >= 2 and top_status in (CandidateStatus.MEETS_ALL_HARD_CONSTRAINTS, CandidateStatus.MEETS_MOST_REQUIREMENTS):
            # Explicit TIE status
            explanation = self._build_5part_explanation(
                primary_eval=tied_top[0],
                all_evals=evaluations,
                requirements=requirements,
                tradeoffs=tradeoffs,
                evidence_registry=evidence_registry,
                is_tie=True,
            )
            recommendations.append(
                Recommendation(
                    recommendation_id=f"rec_{uuid.uuid4().hex[:8]}",
                    status=RecommendationStatus.TIE,
                    stability=RecommendationStability.SENSITIVE_TO_EVIDENCE,
                    candidate=tied_top[0].candidate,
                    tied_candidates=[c.candidate for c in tied_top],
                    explanation=explanation,
                )
            )
            return recommendations

        # Primary Recommendation
        primary_eval = eligible_candidates[0]
        primary_explanation = self._build_5part_explanation(
            primary_eval=primary_eval,
            all_evals=evaluations,
            requirements=requirements,
            tradeoffs=tradeoffs,
            evidence_registry=evidence_registry,
            is_tie=False,
        )

        recommendations.append(
            Recommendation(
                recommendation_id=f"rec_{uuid.uuid4().hex[:8]}",
                status=RecommendationStatus.PRIMARY_RECOMMENDATION,
                stability=stability,
                candidate=primary_eval.candidate,
                explanation=primary_explanation,
            )
        )

        # Alternative Recommendation (if present)
        if len(eligible_candidates) >= 2:
            alt_eval = eligible_candidates[1]
            alt_explanation = self._build_5part_explanation(
                primary_eval=alt_eval,
                all_evals=evaluations,
                requirements=requirements,
                tradeoffs=tradeoffs,
                evidence_registry=evidence_registry,
                is_tie=False,
            )
            recommendations.append(
                Recommendation(
                    recommendation_id=f"rec_{uuid.uuid4().hex[:8]}",
                    status=RecommendationStatus.ALTERNATIVE_RECOMMENDATION,
                    stability=stability,
                    candidate=alt_eval.candidate,
                    explanation=alt_explanation,
                )
            )

        return recommendations

    def _build_5part_explanation(
        self,
        primary_eval: CandidateEvaluation,
        all_evals: List[CandidateEvaluation],
        requirements: List[DecisionRequirement],
        tradeoffs: List[Tradeoff],
        evidence_registry: Dict[str, DecisionEvidence],
        is_tie: bool,
    ) -> RecommendationExplanation:
        # Part 1: Hard constraints satisfied
        hard_sat = [f"Satisfied hard constraint: {r.text}" for r in requirements if r.requirement_id in primary_eval.satisfied_hard_constraints]

        # Part 2: Most important preferences satisfied
        pref_sat = [f"Satisfied preference: {r.text}" for r in requirements if r.requirement_id in primary_eval.constraint_evaluations and primary_eval.constraint_evaluations[r.requirement_id].value == "SATISFIED"]

        # Part 3: Key evidence
        key_ev = []
        for ev_id, ev_item in list(evidence_registry.items())[:3]:
            key_ev.append(ev_item.to_dict())

        # Part 4: Main trade-off
        main_to = [t.description for t in tradeoffs]
        if not main_to:
            main_to = ["No major negative trade-offs identified for this choice."]

        # Part 5: Why alternatives were not selected
        why_not = []
        for other in all_evals:
            if other.candidate.candidate_id != primary_eval.candidate.candidate_id:
                if other.status == CandidateStatus.FAILS_HARD_CONSTRAINT:
                    why_not.append(f"{other.candidate.name} was not selected because it violated hard constraints ({', '.join(other.violated_hard_constraints)}).")
                elif other.status == CandidateStatus.INSUFFICIENT_EVIDENCE:
                    why_not.append(f"{other.candidate.name} had insufficient verified evidence for critical requirements.")
                else:
                    why_not.append(f"{other.candidate.name} ranked lower on soft preferences or cost value.")

        if is_tie:
            why_not.append("Top choices are effectively tied; selection depends on user preference weighting.")

        return RecommendationExplanation(
            hard_constraints_satisfied=hard_sat,
            preferences_satisfied=pref_sat,
            key_evidence=key_ev,
            main_tradeoffs=main_to,
            why_alternatives_not_selected=why_not,
        )


recommendation_engine = RecommendationEngine()
