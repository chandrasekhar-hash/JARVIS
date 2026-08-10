"""
Constraint Evaluation Engine for J.A.R.V.I.S. I2.2 V11 Decision Intelligence.
"""
from typing import Dict, List, Tuple
from intelligence.web.decision.models import (
    CandidateEntity,
    ConstraintStatus,
    ConstraintType,
    DecisionRequirement,
    RequirementType,
)


class ConstraintEngine:
    """
    Evaluates candidates against requirements deterministically.
    Enforces rules: Unknown = INSUFFICIENT_EVIDENCE (never assumed satisfied).
    """

    def evaluate_candidate_constraints(
        self,
        candidate: CandidateEntity,
        requirements: List[DecisionRequirement],
    ) -> Dict[str, ConstraintStatus]:
        results: Dict[str, ConstraintStatus] = {}

        for req in requirements:
            status = self._evaluate_single_requirement(candidate, req)
            results[req.requirement_id] = status

        return results

    def _evaluate_single_requirement(
        self, candidate: CandidateEntity, req: DecisionRequirement
    ) -> ConstraintStatus:
        attrs = candidate.attributes or {}

        # Budget Max / Price Max check
        if req.constraint_type in (ConstraintType.BUDGET_MAX, ConstraintType.PRICE_MAX):
            price_val = attrs.get("price") or attrs.get("cost")
            if price_val is None:
                return ConstraintStatus.UNKNOWN  # INSUFFICIENT_EVIDENCE
            try:
                numeric_price = float(price_val)
                if numeric_price <= req.target_value:
                    return ConstraintStatus.SATISFIED
                else:
                    return ConstraintStatus.NOT_SATISFIED
            except (ValueError, TypeError):
                return ConstraintStatus.UNKNOWN

        # RAM Min check
        if req.constraint_type == ConstraintType.RAM_MIN:
            ram_val = attrs.get("ram") or attrs.get("memory")
            if ram_val is None:
                return ConstraintStatus.UNKNOWN
            try:
                numeric_ram = int(ram_val)
                if numeric_ram >= req.target_value:
                    return ConstraintStatus.SATISFIED
                else:
                    return ConstraintStatus.NOT_SATISFIED
            except (ValueError, TypeError):
                return ConstraintStatus.UNKNOWN

        # Storage Min check
        if req.constraint_type == ConstraintType.STORAGE_MIN:
            st_val = attrs.get("storage") or attrs.get("ssd")
            if st_val is None:
                return ConstraintStatus.UNKNOWN
            try:
                numeric_st = int(st_val)
                if numeric_st >= req.target_value:
                    return ConstraintStatus.SATISFIED
                else:
                    return ConstraintStatus.NOT_SATISFIED
            except (ValueError, TypeError):
                return ConstraintStatus.UNKNOWN

        # Feature Required check
        if req.constraint_type == ConstraintType.FEATURE_REQUIRED:
            target_feat = str(req.target_value).lower()
            cand_features = [str(f).lower() for f in attrs.get("features", [])]
            cand_desc = str(attrs.get("description", "")).lower()

            if any(target_feat in f for f in cand_features) or target_feat in cand_desc:
                return ConstraintStatus.SATISFIED
            return ConstraintStatus.PARTIAL

        return ConstraintStatus.NOT_APPLICABLE


constraint_engine = ConstraintEngine()
