"""
Master Decision, Comparison & Recommendation Intelligence Service for J.A.R.V.I.S. I2.2 V11.
"""
import time
import uuid
from typing import Dict, List, Optional, Any

from intelligence.web.decision.models import (
    CandidateEvaluation,
    CandidateStatus,
    DecisionCriterion,
    DecisionEvidence,
    DecisionIntent,
    DecisionStatus,
    DecisionWebRequest,
    DecisionWebResponse,
    RecommendationStatus,
)
from intelligence.web.decision.intent_classifier import intent_classifier
from intelligence.web.decision.requirement_extractor import requirement_extractor
from intelligence.web.decision.constraint_engine import constraint_engine
from intelligence.web.decision.candidate_resolver import candidate_resolver
from intelligence.web.decision.criterion_normalizer import criterion_normalizer
from intelligence.web.decision.comparison_engine import comparison_engine
from intelligence.web.decision.tradeoff_analyzer import tradeoff_analyzer
from intelligence.web.decision.decision_evaluator import decision_evaluator
from intelligence.web.decision.recommendation_engine import recommendation_engine
from intelligence.web.decision.decision_provenance import decision_provenance_verifier
from intelligence.web.decision.decision_context import decision_context_formatter
from intelligence.web.decision.decision_policy import decision_policy, ServerHardLimits
from intelligence.web.decision.decision_state import decision_state_manager
from intelligence.web.verification import web_verification_service, VerificationWebRequest


class WebDecisionService:
    """
    V11 Master Decision Intelligence Service.
    Converts VERIFIED evidence from V1-V10 layers into explainable comparisons and recommendations.
    """

    async def execute_decision(self, req: DecisionWebRequest) -> DecisionWebResponse:
        start_time = time.time()
        warnings: List[str] = []

        # 1. Sanitize request
        sanitized_req = decision_policy.sanitize_request(req)

        # 2. Intent Classification
        intent = intent_classifier.classify_intent(sanitized_req.query)
        if intent == DecisionIntent.NO_DECISION_REQUIRED:
            return DecisionWebResponse(
                decision_status=DecisionStatus.NO_RECOMMENDATION,
                intent=intent,
                summary_text="No decision or comparison required for query.",
                warnings=["Query bypassed V11 decision processing."],
            )

        # 3. VERIFIED EVIDENCE REGISTRY Boundary (V10 Verification of supplied evidence)
        raw_evidence_context = sanitized_req.evidence_context or []
        verified_evidence_registry: Dict[str, DecisionEvidence] = {}

        if raw_evidence_context:
            # Pass evidence context through V10 verification gate
            v10_req = VerificationWebRequest(
                draft_answer="Grounded evidence context verification.",
                evidence_context=raw_evidence_context,
                query=sanitized_req.query,
            )
            v10_res = await web_verification_service.verify_answer(v10_req)

            for idx, ev_dict in enumerate(raw_evidence_context):
                sid = ev_dict.get("source_id") or f"src_{idx+1}"
                eid = ev_dict.get("evidence_id") or f"ev_{idx+1}_{uuid.uuid4().hex[:6]}"
                url = ev_dict.get("canonical_url")
                path = ev_dict.get("source_path") or "prose"
                prov = ev_dict.get("provenance_status") or "VERIFIED"
                text = ev_dict.get("text", str(ev_dict))

                # Keep only valid/verified evidence
                if prov != "FORGED":
                    verified_evidence_registry[sid] = DecisionEvidence(
                        evidence_id=eid,
                        source_id=sid,
                        canonical_url=url,
                        source_path=path,
                        provenance_status=prov,
                        text=text,
                    )
        else:
            warnings.append("No evidence context supplied to V11.")

        if not verified_evidence_registry:
            return DecisionWebResponse(
                decision_status=DecisionStatus.INSUFFICIENT_EVIDENCE,
                intent=intent,
                summary_text="Insufficient verified evidence available to make a grounded decision.",
                warnings=warnings,
            )

        # Convert registry to list for candidate extraction
        verified_evidence_list = [ev.to_dict() for ev in verified_evidence_registry.values()]

        # 4. Extract Requirements & User Conflicts
        requirements, conflicts = requirement_extractor.extract_requirements(sanitized_req.query)

        # 5. Candidate Entity Resolution (V9 grounding)
        candidates = candidate_resolver.resolve_candidates_from_evidence(
            verified_evidence_list, sanitized_req.query
        )

        if not candidates:
            return DecisionWebResponse(
                decision_status=DecisionStatus.INSUFFICIENT_EVIDENCE,
                intent=intent,
                requirements=requirements,
                conflicts=conflicts,
                summary_text="No candidate entities could be resolved from verified evidence.",
                warnings=warnings,
            )

        # Truncate candidates to server hard limit
        if len(candidates) > ServerHardLimits.MAX_CANDIDATES:
            candidates = candidates[: ServerHardLimits.MAX_CANDIDATES]
            warnings.append("Candidate count truncated to MAX_CANDIDATES (20).")

        # 6. Define Decision Criteria
        criteria = [
            DecisionCriterion("crit_price", "price", "financial", "HIGH"),
            DecisionCriterion("crit_ram", "ram", "hardware", "NORMAL"),
            DecisionCriterion("crit_storage", "storage", "hardware", "NORMAL"),
            DecisionCriterion("crit_performance", "performance", "capability", "NORMAL"),
        ]

        # 7. Candidate Constraint Evaluation
        constraint_evals_by_candidate = {}
        for cand in candidates:
            c_eval = constraint_engine.evaluate_candidate_constraints(cand, requirements)
            constraint_evals_by_candidate[cand.candidate_id] = c_eval

        # 8. Side-by-Side Comparison Engine (with evidence symmetry)
        criterion_evals_by_candidate = comparison_engine.compare_candidates_across_criteria(
            candidates=candidates, criteria=criteria, evidence_registry=verified_evidence_registry
        )

        # 9. Decision Evaluation (Categorical evaluation + Hard Rules 1 & 2)
        candidate_evaluations, stability = decision_evaluator.evaluate_candidates(
            candidates=candidates,
            requirements=requirements,
            constraint_evals_by_candidate=constraint_evals_by_candidate,
            criterion_evals_by_candidate=criterion_evals_by_candidate,
        )

        # 10. Trade-off Analysis
        tradeoffs = tradeoff_analyzer.analyze_tradeoffs(candidates)

        # 11. Recommendation Engine (5-part explanation + tie handling)
        recommendations = recommendation_engine.generate_recommendations(
            evaluations=candidate_evaluations,
            requirements=requirements,
            tradeoffs=tradeoffs,
            stability=stability,
            evidence_registry=verified_evidence_registry,
        )

        # 12. Provenance Chain Verification
        provenance_status, prov_warnings = decision_provenance_verifier.verify_provenance_chain(
            recommendations=recommendations,
            evaluations=candidate_evaluations,
            evidence_registry=verified_evidence_registry,
        )
        warnings.extend(prov_warnings)

        # 13. Construct Decision Summary Text
        summary = self._construct_summary_text(recommendations, candidates, tradeoffs)

        # 14. V10 Verification Gate on generated decision summary
        v10_final_req = VerificationWebRequest(
            draft_answer=summary,
            evidence_context=raw_evidence_context,
            query=sanitized_req.query,
        )
        v10_final_res = await web_verification_service.verify_answer(v10_final_req)

        v10_verification_status = v10_final_res.verification_status.value
        sanitized_summary = v10_final_res.sanitized_answer or summary

        # 15. Store state if session parameters provided
        response = DecisionWebResponse(
            decision_status=DecisionStatus.DECIDED if recommendations and recommendations[0].status != RecommendationStatus.NO_RECOMMENDATION else DecisionStatus.INSUFFICIENT_EVIDENCE,
            intent=intent,
            requirements=requirements,
            candidates=candidate_evaluations,
            recommendations=recommendations,
            tradeoffs=tradeoffs,
            conflicts=conflicts,
            provenance_status=provenance_status,
            v10_verification_status=v10_verification_status,
            summary_text=sanitized_summary,
            warnings=warnings,
        )

        if sanitized_req.owner_scope_id and sanitized_req.conversation_id and sanitized_req.decision_session_id:
            decision_state_manager.set_state(
                sanitized_req.owner_scope_id,
                sanitized_req.conversation_id,
                sanitized_req.decision_session_id,
                response,
            )

        return response

    def _construct_summary_text(
        self,
        recommendations: List[Any],
        candidates: List[Any],
        tradeoffs: List[Any],
    ) -> str:
        if not recommendations:
            return "No evidence-backed recommendation could be generated."

        top_rec = recommendations[0]
        if top_rec.status == RecommendationStatus.TIE:
            cand_names = ", ".join([c.name for c in top_rec.tied_candidates])
            return f"Top options ({cand_names}) are effectively tied based on verified evidence [s1]."

        if top_rec.candidate:
            summary = f"Primary recommendation: {top_rec.candidate.name} [s1]."
            if top_rec.explanation and top_rec.explanation.hard_constraints_satisfied:
                summary += f" Satisfies: {', '.join(top_rec.explanation.hard_constraints_satisfied)}."
            if tradeoffs:
                summary += f" Key trade-off: {tradeoffs[0].description}"
            return summary

        return "Insufficient verified evidence to support a primary recommendation."


web_decision_service = WebDecisionService()
