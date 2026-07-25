import re
import time
from typing import Dict, List, Optional, Any, Set, Tuple
from cognitive.config import cognitive_config, CognitiveConfig
from cognitive.models import (
    StrategyType,
    RiskLevel,
    PolicyViolationType,
    StrategyRecommendation,
    CognitiveAssessment,
    PolicyValidationResult,
)
from cognitive.policy_engine import cognitive_policy_engine, CognitivePolicyEngine
from cognitive.experience_repository import experience_repository, ExperienceRepository
from tools.telemetry import log_structured, backend_log


class CognitiveReasoningEngine:
    """
    Pre-Execution Cognitive Reasoning Engine.
    Executes a 9-stage cognitive reasoning pipeline before task graph generation:
    1. Goal Analysis
    2. Intent Classification
    3. Constraint Extraction
    4. Experience Retrieval
    5. Risk Assessment
    6. Strategy Generation
    7. Strategy Comparison
    8. Confidence Calculation
    9. Final Recommendation

    MUST NOT execute any task, perform reflection, or trigger replanning.
    """

    def __init__(
        self,
        config: Optional[CognitiveConfig] = None,
        policy_engine: Optional[CognitivePolicyEngine] = None,
        exp_repo: Optional[ExperienceRepository] = None
    ):
        self.config = config or cognitive_config
        self.policy_engine = policy_engine or cognitive_policy_engine
        self.exp_repo = exp_repo or experience_repository

    async def analyze_and_assess_goal(
        self,
        goal_id: str,
        goal_title: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        user_constraints: Optional[List[str]] = None
    ) -> CognitiveAssessment:
        """
        Executes complete pre-execution cognitive reasoning pipeline.
        Returns a structured CognitiveAssessment.
        """
        start_time = time.time()
        goal_title_str = goal_title or ""
        desc_str = description or ""
        meta_dict = metadata or {}
        context_dict = context or {}
        constraints_list = user_constraints or []

        # Stage 1: Goal Analysis
        analysis = self._stage1_goal_analysis(goal_title_str, desc_str, constraints_list)

        # Stage 2: Intent Classification
        intent = self._stage2_intent_classification(goal_title_str, desc_str)

        # Stage 3: Constraint Extraction
        extracted_constraints = self._stage3_constraint_extraction(analysis, meta_dict, constraints_list)

        # Stage 4: Experience Retrieval
        matched_experiences, failure_patterns = await self._stage4_experience_retrieval(goal_title_str)

        # Stage 5: Risk Assessment
        risk_level = self._stage5_risk_assessment(goal_title_str, desc_str, meta_dict, failure_patterns)

        # Stage 6: Strategy Generation
        candidate_strategies = self._stage6_strategy_generation(analysis, intent, risk_level, matched_experiences)

        # Stage 7: Strategy Comparison
        recommended_strategy, alt_strategies = self._stage7_strategy_comparison(candidate_strategies, risk_level)

        # Stage 8: Confidence Calculation
        confidence_score, success_prob, reasoning_notes = self._stage8_confidence_calculation(
            analysis=analysis,
            risk_level=risk_level,
            strategy=recommended_strategy,
            matched_experiences=matched_experiences,
            failure_patterns=failure_patterns,
            extracted_constraints=extracted_constraints
        )

        # Stage 9: Final Recommendation & Policy Validation
        exp_ids = [exp["memory_id"] for exp in matched_experiences]

        assessment = CognitiveAssessment(
            goal_id=goal_id or "goal_unknown",
            confidence_score=confidence_score,
            risk_level=risk_level,
            recommended_strategy=recommended_strategy,
            matched_experience_ids=exp_ids,
            reasoning_summary=f"Strategy '{recommended_strategy.value}' selected ({intent}). {reasoning_notes}",
            approved=True,
            alternative_strategies=alt_strategies,
            estimated_complexity=analysis["complexity"],
            estimated_success_probability=success_prob
        )

        # Validate with Policy Engine
        policy_res = self.policy_engine.evaluate_assessment(assessment)
        if not policy_res.is_valid:
            # Policy rejected assessment -> Return fallback unapproved assessment
            assessment = CognitiveAssessment(
                goal_id=goal_id or "goal_unknown",
                confidence_score=min(confidence_score, policy_res.confidence_score),
                risk_level=policy_res.risk_level,
                recommended_strategy=StrategyType.FEASIBILITY_PROBING if recommended_strategy == StrategyType.DIRECT_EXECUTION else recommended_strategy,
                matched_experience_ids=exp_ids,
                reasoning_summary=f"Policy Warning: {'; '.join(policy_res.violations)}. {reasoning_notes}",
                approved=False,
                alternative_strategies=alt_strategies,
                estimated_complexity=analysis["complexity"],
                estimated_success_probability=max(0.1, success_prob - 0.3)
            )

        elapsed_ms = (time.time() - start_time) * 1000.0
        log_structured(backend_log, "INFO", f"[ReasoningEngine] Goal '{goal_id}' assessed in {elapsed_ms:.1f}ms (Strategy: {assessment.recommended_strategy.value}, Confidence: {assessment.confidence_score:.2f}, Risk: {assessment.risk_level.value})")

        return assessment

    # ── Pipeline Stages ──────────────────────────────────────────────────────

    def _stage1_goal_analysis(self, title: str, desc: str, user_constraints: List[str]) -> Dict[str, Any]:
        full_text = f"{title} {desc}".strip()
        words = full_text.split()
        word_count = len(words)

        # Detect ambiguity markers
        ambiguity_markers = ["maybe", "or something", "stuff", "whatever", "somehow", "etc", "try to", "kind of"]
        ambiguity_count = sum(1 for marker in ambiguity_markers if marker in full_text.lower())
        is_ambiguous = ambiguity_count > 0 or word_count < 2

        # Complexity estimation (1.0 to 10.0 scale)
        reasoning_keywords = ["build", "develop", "organize", "refactor", "migrate", "search", "all", "every", "clean"]
        keyword_hits = sum(1 for kw in reasoning_keywords if kw in full_text.lower())
        complexity = min(10.0, max(1.0, 2.0 + (word_count * 0.2) + (keyword_hits * 1.5) + (len(user_constraints) * 1.0)))

        return {
            "full_text": full_text,
            "word_count": word_count,
            "is_ambiguous": is_ambiguous,
            "ambiguity_count": ambiguity_count,
            "complexity": round(complexity, 1)
        }

    def _stage2_intent_classification(self, title: str, desc: str) -> str:
        text = f"{title} {desc}".lower()
        if any(w in text for w in ["open", "launch", "close", "switch", "focus", "window"]):
            return "APPLICATION_CONTROL"
        elif any(w in text for w in ["delete", "remove", "move", "copy", "read", "file", "folder", "directory"]):
            return "FILE_MANAGEMENT"
        elif any(w in text for w in ["search", "find", "google", "browser", "url", "http", "lookup"]):
            return "INFORMATION_RETRIEVAL"
        elif any(w in text for w in ["build", "create", "develop", "organize", "batch", "automate", "pipeline"]):
            return "COMPLEX_AUTOMATION"
        else:
            return "GENERAL_ASSISTANCE"

    def _stage3_constraint_extraction(self, analysis: Dict[str, Any], metadata: Dict[str, Any], user_constraints: List[str]) -> List[str]:
        constraints = list(user_constraints)
        if metadata.get("max_depth"):
            constraints.append(f"MaxDepth: {metadata['max_depth']}")
        if metadata.get("timeout"):
            constraints.append(f"Timeout: {metadata['timeout']}s")
        if analysis["is_ambiguous"]:
            constraints.append("RequireAmbiguityResolution")
        return constraints

    async def _stage4_experience_retrieval(self, title: str) -> Tuple[List[Dict[str, Any]], List[Any]]:
        try:
            matched_experiences = await self.exp_repo.search_similar_experiences(
                query_text=title,
                experience_type="workflow_template",
                limit=3
            )
            # Filter out experiences with low relevance match (< 0.5) to query
            relevant_matched = [exp for exp in matched_experiences if exp.get("relevance_score", 0.0) >= 0.5]

            failure_patterns = await self.exp_repo.get_failure_patterns(error_signature=title, limit=3)
            return relevant_matched, failure_patterns
        except Exception as e:
            log_structured(backend_log, "WARNING", f"[ReasoningEngine] Experience retrieval fallback: {str(e)}")
            return [], []

    def _stage5_risk_assessment(
        self,
        title: str,
        desc: str,
        metadata: Dict[str, Any],
        failure_patterns: List[Any]
    ) -> RiskLevel:
        text = f"{title} {desc}".lower()

        # Check policy engine goal validation for path restrictions
        policy_goal_res = self.policy_engine.validate_goal(
            goal_id="temp_check",
            goal_title=title,
            description=desc,
            metadata=metadata
        )
        if not policy_goal_res.is_valid and policy_goal_res.violation_type == PolicyViolationType.PATH_RESTRICTION:
            return RiskLevel.CRITICAL

        # Critical risk triggers
        if any(re.search(re.escape(pattern), text, re.IGNORECASE) for pattern in ["system32", "windows", "registry", "rm -rf", "format c:", "drop database"]):
            return RiskLevel.CRITICAL

        # High risk triggers
        if any(kw in text for kw in ["delete all", "wipe", "force kill", "shutdown", "uninstall"]) or len(failure_patterns) >= 2:
            return RiskLevel.HIGH

        # Medium risk triggers
        if any(kw in text for kw in ["delete", "remove", "modify", "overwrite", "batch", "organize"]):
            return RiskLevel.MEDIUM

        return RiskLevel.LOW

    def _stage6_strategy_generation(
        self,
        analysis: Dict[str, Any],
        intent: str,
        risk_level: RiskLevel,
        matched_experiences: List[Dict[str, Any]]
    ) -> List[StrategyType]:
        candidates: List[StrategyType] = []

        # Rule A: Simple, low-risk application/system queries -> DIRECT_EXECUTION
        if risk_level == RiskLevel.LOW and analysis["complexity"] <= 3.5 and not analysis["is_ambiguous"]:
            candidates.append(StrategyType.DIRECT_EXECUTION)

        # Rule B: Complex or multi-step goals -> HIERARCHICAL_DECOMPOSITION
        if analysis["complexity"] >= 4.0 or intent in ("COMPLEX_AUTOMATION", "FILE_MANAGEMENT") or len(matched_experiences) > 0:
            candidates.append(StrategyType.HIERARCHICAL_DECOMPOSITION)

        # Rule C: Ambiguous queries -> EXPLORATORY_SEARCH
        if analysis["is_ambiguous"] or intent == "INFORMATION_RETRIEVAL":
            candidates.append(StrategyType.EXPLORATORY_SEARCH)

        # Rule D: High/Critical risk -> FEASIBILITY_PROBING
        if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            candidates.append(StrategyType.FEASIBILITY_PROBING)

        if not candidates:
            candidates.append(StrategyType.HIERARCHICAL_DECOMPOSITION)

        return candidates

    def _stage7_strategy_comparison(
        self,
        candidates: List[StrategyType],
        risk_level: RiskLevel
    ) -> Tuple[StrategyType, List[StrategyType]]:
        # Filter out forbidden combinations
        valid_candidates = []
        for cand in candidates:
            if cand == StrategyType.DIRECT_EXECUTION and risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
                continue
            valid_candidates.append(cand)

        if not valid_candidates:
            valid_candidates = [StrategyType.FEASIBILITY_PROBING if risk_level == RiskLevel.CRITICAL else StrategyType.HIERARCHICAL_DECOMPOSITION]

        primary_strategy = valid_candidates[0]
        alternatives = [c for c in candidates if c != primary_strategy]

        return primary_strategy, alternatives

    def _stage8_confidence_calculation(
        self,
        analysis: Dict[str, Any],
        risk_level: RiskLevel,
        strategy: StrategyType,
        matched_experiences: List[Dict[str, Any]],
        failure_patterns: List[Any],
        extracted_constraints: List[str]
    ) -> Tuple[float, float, str]:
        base_confidence = 0.85
        notes: List[str] = []

        # 1. Experience Similarity Bonus
        if matched_experiences:
            top_rank = matched_experiences[0].get("rank_score", 0.5)
            bonus = min(0.15, top_rank * 0.15)
            base_confidence += bonus
            notes.append(f"Matched past experience (+{bonus:.2f})")

        # 2. Failure Pattern Penalty
        if failure_patterns:
            penalty = min(0.30, len(failure_patterns) * 0.15)
            base_confidence -= penalty
            notes.append(f"Matching failure patterns detected (-{penalty:.2f})")

        # 3. Ambiguity Penalty
        if analysis["is_ambiguous"]:
            base_confidence -= 0.20
            notes.append("Goal is ambiguous (-0.20)")

        # 4. Risk Level Adjustment
        if risk_level == RiskLevel.HIGH:
            base_confidence -= 0.15
            notes.append("HIGH execution risk (-0.15)")
        elif risk_level == RiskLevel.CRITICAL:
            base_confidence -= 0.35
            notes.append("CRITICAL execution risk (-0.35)")

        # 5. Complexity Adjustment
        if analysis["complexity"] > 7.0:
            base_confidence -= 0.10
            notes.append("High task complexity (-0.10)")

        # Clamp confidence to [0.0, 1.0]
        final_confidence = max(0.0, min(1.0, base_confidence))
        estimated_success_prob = max(0.05, min(0.99, final_confidence * 0.95))

        reasoning_text = "; ".join(notes) if notes else "High feasibility confidence."
        return round(final_confidence, 2), round(estimated_success_prob, 2), reasoning_text


cognitive_reasoning_engine = CognitiveReasoningEngine()
