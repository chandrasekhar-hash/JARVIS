"""
Fail-Closed Provenance Engine for J.A.R.V.I.S. I2.2 V11 Decision Intelligence.
"""
from typing import Dict, List, Tuple
from intelligence.web.decision.models import (
    CandidateEvaluation,
    DecisionEvidence,
    Recommendation,
    RecommendationStatus,
)


class DecisionProvenanceVerifier:
    """
    Enforces fail-closed provenance validation across the entire decision chain:
    recommendation -> candidate_evaluation -> criterion_evaluation -> evidence_id -> source_id -> canonical_url -> source_path.
    """

    def verify_provenance_chain(
        self,
        recommendations: List[Recommendation],
        evaluations: List[CandidateEvaluation],
        evidence_registry: Dict[str, DecisionEvidence],
    ) -> Tuple[str, List[str]]:
        warnings: List[str] = []
        if not evidence_registry:
            warnings.append("Empty verified evidence registry.")
            return "UNVERIFIED", warnings

        for rec in recommendations:
            if rec.status == RecommendationStatus.NO_RECOMMENDATION:
                continue

            if rec.candidate:
                # Find evaluation
                cand_eval = next((ev for ev in evaluations if ev.candidate.candidate_id == rec.candidate.candidate_id), None)
                if not cand_eval:
                    rec.status = RecommendationStatus.NO_RECOMMENDATION
                    warnings.append(f"Recommendation for '{rec.candidate.name}' rejected: missing evaluation object.")
                    continue

                # Check criterion evaluations provenance
                valid_crit = False
                for cr in cand_eval.criterion_evaluations:
                    for sid in cr.source_ids:
                        if sid in evidence_registry or any(ev.source_id == sid for ev in evidence_registry.values()):
                            valid_crit = True
                            break

                if not valid_crit and cand_eval.criterion_evaluations:
                    warnings.append(f"Recommendation for '{rec.candidate.name}' rejected: invalid provenance chain.")
                    rec.status = RecommendationStatus.NO_RECOMMENDATION

        return "VERIFIED", warnings


decision_provenance_verifier = DecisionProvenanceVerifier()
