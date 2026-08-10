"""
Side-by-Side Evidence-Backed Comparison Engine for J.A.R.V.I.S. I2.2 V11 Decision Intelligence.
"""
from typing import Dict, List, Optional, Any
from intelligence.web.decision.models import (
    CandidateEntity,
    CriterionEvaluation,
    CriterionStatus,
    DecisionCriterion,
    DecisionEvidence,
)


class ComparisonEngine:
    """
    Generates side-by-side evidence-backed comparisons across criteria.
    Enforces Evidence Symmetry: missing data for one candidate is classified as INSUFFICIENT_EVIDENCE
    and is NEVER interpreted as evidence against that candidate.
    """

    def compare_candidates_across_criteria(
        self,
        candidates: List[CandidateEntity],
        criteria: List[DecisionCriterion],
        evidence_registry: Dict[str, DecisionEvidence],
    ) -> Dict[str, List[CriterionEvaluation]]:
        evaluations_by_candidate: Dict[str, List[CriterionEvaluation]] = {}

        for cand in candidates:
            cand_evals: List[CriterionEvaluation] = []
            for crit in criteria:
                eval_item = self._evaluate_criterion_for_candidate(
                    cand, crit, evidence_registry
                )
                cand_evals.append(eval_item)
            evaluations_by_candidate[cand.candidate_id] = cand_evals

        return evaluations_by_candidate

    def _evaluate_criterion_for_candidate(
        self,
        candidate: CandidateEntity,
        criterion: DecisionCriterion,
        evidence_registry: Dict[str, DecisionEvidence],
    ) -> CriterionEvaluation:
        attrs = candidate.attributes or {}
        crit_key = criterion.name.lower()
        raw_val = attrs.get(crit_key) or attrs.get(criterion.category)

        # Match evidence items backing this candidate & criterion
        matching_ev_ids = []
        matching_s_ids = []
        matching_urls = []

        for ev in evidence_registry.values():
            if candidate.name.lower() in ev.text.lower():
                matching_ev_ids.append(ev.evidence_id)
                matching_s_ids.append(ev.source_id)
                if ev.canonical_url:
                    matching_urls.append(ev.canonical_url)

        if raw_val is None:
            # Enforce evidence symmetry: missing evidence = INSUFFICIENT_EVIDENCE
            return CriterionEvaluation(
                criterion_id=criterion.criterion_id,
                candidate_id=candidate.candidate_id,
                status=CriterionStatus.INSUFFICIENT_EVIDENCE,
                raw_value=None,
                normalized_value=None,
                unit=None,
                evidence_ids=matching_ev_ids,
                source_ids=matching_s_ids,
                canonical_urls=matching_urls,
            )

        return CriterionEvaluation(
            criterion_id=criterion.criterion_id,
            candidate_id=candidate.candidate_id,
            status=CriterionStatus.EVIDENCE_VERIFIED,
            raw_value=raw_val,
            normalized_value=raw_val,
            unit="GB" if "ram" in crit_key or "storage" in crit_key else "INR" if "price" in crit_key else None,
            evidence_ids=matching_ev_ids,
            source_ids=matching_s_ids,
            canonical_urls=matching_urls,
        )


comparison_engine = ComparisonEngine()
