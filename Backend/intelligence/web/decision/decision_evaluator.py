"""
Categorical Decision Evaluator Engine for J.A.R.V.I.S. I2.2 V11 Decision Intelligence.
"""
from typing import Dict, List, Tuple
from intelligence.web.decision.models import (
    CandidateEntity,
    CandidateEvaluation,
    CandidateStatus,
    ConstraintStatus,
    CriterionEvaluation,
    DecisionRequirement,
    RecommendationStability,
    RequirementType,
)


class DecisionEvaluator:
    """
    Evaluates candidate status categorically and enforces critical hard rules:
    Rule 1: A candidate failing a HARD_CONSTRAINT MUST be marked FAILS_HARD_CONSTRAINT, excluded from PRIMARY_RECOMMENDATION, and cannot outrank candidates satisfying all hard constraints.
    Rule 2: A candidate with INSUFFICIENT_EVIDENCE (UNKNOWN) for a HARD_CONSTRAINT cannot be treated as equivalent to one that satisfies that constraint.
    """

    def evaluate_candidates(
        self,
        candidates: List[CandidateEntity],
        requirements: List[DecisionRequirement],
        constraint_evals_by_candidate: Dict[str, Dict[str, ConstraintStatus]],
        criterion_evals_by_candidate: Dict[str, List[CriterionEvaluation]],
    ) -> Tuple[List[CandidateEvaluation], RecommendationStability]:
        evaluations: List[CandidateEvaluation] = []

        hard_reqs = [r for r in requirements if r.requirement_type == RequirementType.HARD_CONSTRAINT]

        for cand in candidates:
            c_evals = constraint_evals_by_candidate.get(cand.candidate_id, {})
            cr_evals = criterion_evals_by_candidate.get(cand.candidate_id, [])

            satisfied_hard: List[str] = []
            violated_hard: List[str] = []
            unverified_hard: List[str] = []

            for h_req in hard_reqs:
                st = c_evals.get(h_req.requirement_id, ConstraintStatus.UNKNOWN)
                if st == ConstraintStatus.SATISFIED:
                    satisfied_hard.append(h_req.requirement_id)
                elif st == ConstraintStatus.NOT_SATISFIED:
                    violated_hard.append(h_req.requirement_id)
                else:  # UNKNOWN / PARTIAL / NOT_APPLICABLE
                    unverified_hard.append(h_req.requirement_id)

            # Categorical Status Determination
            if violated_hard:
                cand_status = CandidateStatus.FAILS_HARD_CONSTRAINT
            elif unverified_hard:
                cand_status = CandidateStatus.INSUFFICIENT_EVIDENCE
            elif hard_reqs and len(satisfied_hard) == len(hard_reqs):
                cand_status = CandidateStatus.MEETS_ALL_HARD_CONSTRAINTS
            elif satisfied_hard:
                cand_status = CandidateStatus.MEETS_MOST_REQUIREMENTS
            else:
                cand_status = CandidateStatus.PARTIAL_MATCH

            evaluations.append(
                CandidateEvaluation(
                    candidate=cand,
                    status=cand_status,
                    constraint_evaluations=c_evals,
                    criterion_evaluations=cr_evals,
                    satisfied_hard_constraints=satisfied_hard,
                    violated_hard_constraints=violated_hard,
                    unverified_hard_constraints=unverified_hard,
                )
            )

        # Sort evaluations enforcing Hard Rule 1 & Rule 2:
        # 1. MEETS_ALL_HARD_CONSTRAINTS first
        # 2. MEETS_MOST_REQUIREMENTS
        # 3. INSUFFICIENT_EVIDENCE
        # 4. PARTIAL_MATCH
        # 5. FAILS_HARD_CONSTRAINT last
        status_priority = {
            CandidateStatus.MEETS_ALL_HARD_CONSTRAINTS: 0,
            CandidateStatus.MEETS_MOST_REQUIREMENTS: 1,
            CandidateStatus.PARTIAL_MATCH: 2,
            CandidateStatus.INSUFFICIENT_EVIDENCE: 3,
            CandidateStatus.FAILS_HARD_CONSTRAINT: 4,
        }

        evaluations.sort(key=lambda ev: status_priority.get(ev.status, 5))

        # Assess Recommendation Stability
        stability = RecommendationStability.STABLE
        if not evaluations:
            stability = RecommendationStability.UNSTABLE
        elif len(evaluations) >= 2 and evaluations[0].status == evaluations[1].status:
            stability = RecommendationStability.SENSITIVE_TO_EVIDENCE

        return evaluations, stability


decision_evaluator = DecisionEvaluator()
