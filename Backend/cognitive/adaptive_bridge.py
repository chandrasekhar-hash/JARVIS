import time
from typing import Dict, List, Optional, Any, Tuple
from cognitive.config import cognitive_config, CognitiveConfig
from cognitive.models import (
    StrategyType,
    RiskLevel,
    GoalOutcome,
    CognitiveAssessment,
    ReflectionReport,
    WorkflowTemplate,
    FailurePattern,
    AdaptationPlan,
)
from cognitive.policy_engine import cognitive_policy_engine, CognitivePolicyEngine
from cognitive.experience_repository import experience_repository, ExperienceRepository
from tools.telemetry import log_structured, backend_log


class AdaptivePlannerBridge:
    """
    Adaptive Planner Bridge.
    Acts as a decision bridge between the Cognitive Layer and the execution planner.
    Executes a 9-stage plan adaptation pipeline:
    1. Plan Inspection
    2. Historical Comparison
    3. Reflection Analysis
    4. Risk Review
    5. Adaptation Generation
    6. Plan Optimisation
    7. Safety Validation
    8. Adaptation Report
    9. AdaptationPlan Output

    MUST NOT execute workflows, perform reflection, or manage multiple goals directly.
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

    async def adapt_execution_plan(
        self,
        goal_id: str,
        assessment: CognitiveAssessment,
        current_plan: List[Dict[str, Any]],
        workflow_template: Optional[WorkflowTemplate] = None,
        reflection_history: Optional[List[ReflectionReport]] = None,
        user_constraints: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AdaptationPlan:
        """
        Executes complete cognitive plan adaptation pipeline.
        Returns a structured AdaptationPlan.
        """
        start_time = time.time()
        plan_list = current_plan or []
        reflections = reflection_history or []
        constraints = user_constraints or []
        meta = metadata or {}

        # Stage 1: Plan Inspection
        plan_summary = self._stage1_plan_inspection(plan_list, assessment)

        # Stage 2: Historical Comparison
        historical_matches = await self._stage2_historical_comparison(assessment.reasoning_summary, workflow_template)

        # Stage 3: Reflection Analysis
        historical_failures, recent_reflections = await self._stage3_reflection_analysis(reflections, plan_list)

        # Stage 4: Risk Review
        risk_level, safety_violations = self._stage4_risk_review(assessment, plan_list, historical_failures)

        # Stage 5: Adaptation Generation
        strategy, decomp_changes, retry_policy = self._stage5_adaptation_generation(
            assessment=assessment,
            plan_list=plan_list,
            historical_matches=historical_matches,
            historical_failures=historical_failures
        )

        # Stage 6: Plan Optimisation
        reordered_tasks, parallel_recs = self._stage6_plan_optimisation(plan_list, decomp_changes)

        # Stage 7: Safety Validation
        policy_res = self.policy_engine.approve_strategy(strategy, risk_level, assessment.confidence_score)
        approved = policy_res.is_valid and not safety_violations

        # Stage 8 & 9: Adaptation Report & Output
        resource_recs = self._stage8_resource_recommendations(plan_summary, meta)
        improvement = self._calculate_improvement(outcome_score=0.85 if approved else 0.40, historical_failures=historical_failures)

        summary_text = (
            f"Adapted strategy to '{strategy.value}'. "
            f"Optimized task sequence ({len(reordered_tasks)} tasks, {len(parallel_recs)} parallel groups). "
            f"Safety validation: {'APPROVED' if approved else 'REJECTED BY POLICY'}."
        )

        plan = AdaptationPlan(
            goal_id=goal_id or "goal_unknown",
            adapted_strategy=strategy,
            recommended_task_order=reordered_tasks,
            decomposition_changes=decomp_changes,
            retry_policy=retry_policy,
            parallelisation_recommendations=parallel_recs,
            resource_recommendations=resource_recs,
            estimated_improvement=round(improvement, 2),
            adaptation_summary=summary_text,
            approved=approved
        )

        elapsed_ms = (time.time() - start_time) * 1000.0
        log_structured(backend_log, "INFO", f"[AdaptiveBridge] Goal '{goal_id}' adapted in {elapsed_ms:.1f}ms (Strategy: {strategy.value}, Approved: {approved})")

        return plan

    # ── Pipeline Stages ──────────────────────────────────────────────────────

    def _stage1_plan_inspection(self, plan_list: List[Dict[str, Any]], assessment: CognitiveAssessment) -> Dict[str, Any]:
        task_names = [t.get("task_name", f"task_{i}") for i, t in enumerate(plan_list)]
        tools_used = [t.get("tool_name") or t.get("suggested_tool") for t in plan_list if t.get("tool_name") or t.get("suggested_tool")]
        return {
            "total_tasks": len(plan_list),
            "task_names": task_names,
            "tools_used": tools_used,
            "assessment_strategy": assessment.recommended_strategy
        }

    async def _stage2_historical_comparison(
        self,
        query: str,
        provided_template: Optional[WorkflowTemplate]
    ) -> List[Dict[str, Any]]:
        matches: List[Dict[str, Any]] = []
        if provided_template:
            matches.append({"template_id": provided_template.template_id, "data": provided_template.model_dump()})

        try:
            exp_matches = await self.exp_repo.search_similar_experiences(
                query_text=query,
                experience_type="workflow_template",
                limit=3
            )
            matches.extend(exp_matches)
        except Exception as e:
            log_structured(backend_log, "WARNING", f"[AdaptiveBridge] Historical comparison fallback: {str(e)}")

        return matches

    async def _stage3_reflection_analysis(
        self,
        reflections: List[ReflectionReport],
        plan_list: List[Dict[str, Any]]
    ) -> Tuple[List[FailurePattern], List[ReflectionReport]]:
        failures: List[FailurePattern] = []
        tools_in_plan = [t.get("tool_name") or t.get("suggested_tool") for t in plan_list if t.get("tool_name") or t.get("suggested_tool")]

        for tool in tools_in_plan:
            try:
                pats = await self.exp_repo.get_failure_patterns(error_signature=tool, limit=2)
                failures.extend(pats)
            except Exception:
                continue

        return failures, reflections

    def _stage4_risk_review(
        self,
        assessment: CognitiveAssessment,
        plan_list: List[Dict[str, Any]],
        failures: List[FailurePattern]
    ) -> Tuple[RiskLevel, List[str]]:
        risk = assessment.risk_level
        violations: List[str] = []

        # If multiple historical failure patterns exist for this toolset -> Elevate risk
        if len(failures) >= 2 and risk == RiskLevel.LOW:
            risk = RiskLevel.MEDIUM
        elif len(failures) >= 4 and risk in (RiskLevel.LOW, RiskLevel.MEDIUM):
            risk = RiskLevel.HIGH

        if risk == RiskLevel.CRITICAL and assessment.recommended_strategy == StrategyType.DIRECT_EXECUTION:
            violations.append("Direct execution forbidden for CRITICAL risk level.")

        return risk, violations

    def _stage5_adaptation_generation(
        self,
        assessment: CognitiveAssessment,
        plan_list: List[Dict[str, Any]],
        historical_matches: List[Dict[str, Any]],
        historical_failures: List[FailurePattern]
    ) -> Tuple[StrategyType, List[Dict[str, Any]], Dict[str, Any]]:
        strategy = assessment.recommended_strategy
        decomp_changes: List[Dict[str, Any]] = []

        # Default retry policy
        retry_policy = {
            "max_retries": self.config.MAX_TASK_RETRIES,
            "retry_delay_sec": 1.0,
            "exponential_backoff": True
        }

        # If failures detected -> Switch strategy or add feasibility probing step
        if historical_failures:
            if strategy == StrategyType.DIRECT_EXECUTION:
                strategy = StrategyType.HIERARCHICAL_DECOMPOSITION

            retry_policy["max_retries"] = min(5, self.config.MAX_TASK_RETRIES + 1)
            retry_policy["retry_delay_sec"] = 2.0

            decomp_changes.append({
                "action": "insert_step",
                "position": 0,
                "step_name": "Verify Environment & Permissions",
                "reason": f"Avoid recurring failure: {historical_failures[0].error_signature[:40]}"
            })

        # If historical workflow template exists -> Adapt decomposition to template
        if historical_matches and len(plan_list) < len(historical_matches[0].get("data", {}).get("recommended_tasks", [])):
            decomp_changes.append({
                "action": "expand_decomposition",
                "recommended_template": historical_matches[0].get("template_id"),
                "reason": "Align task structure with proven historical workflow template"
            })

        return strategy, decomp_changes, retry_policy

    def _stage6_plan_optimisation(
        self,
        plan_list: List[Dict[str, Any]],
        decomp_changes: List[Dict[str, Any]]
    ) -> Tuple[List[str], List[str]]:
        task_names = [t.get("task_name", f"task_{i}") for i, t in enumerate(plan_list)]

        # Insert extra step if required
        for change in decomp_changes:
            if change.get("action") == "insert_step":
                step_name = change.get("step_name", "Verification Step")
                if step_name not in task_names:
                    task_names.insert(change.get("position", 0), step_name)

        # Identify potential parallel execution opportunities
        parallel_recs: List[str] = []
        if len(task_names) >= 2:
            read_tasks = [t for t in task_names if any(w in t.lower() for w in ["read", "search", "check", "verify", "list"])]
            if len(read_tasks) >= 2:
                parallel_recs.append(f"Execute read-only tasks in parallel: {', '.join(read_tasks)}")

        return task_names, parallel_recs

    def _stage8_resource_recommendations(self, plan_summary: Dict[str, Any], meta: Dict[str, Any]) -> List[str]:
        recs: List[str] = []
        if plan_summary["total_tasks"] > 5:
            recs.append("Task graph is deep (>5 tasks); allocate increased execution timeout.")
        if any(t in ("browser_open_url", "browser_control") for t in plan_summary["tools_used"]):
            recs.append("Ensure browser session context is active prior to execution.")

        return recs

    def _calculate_improvement(self, outcome_score: float, historical_failures: List[FailurePattern]) -> float:
        base_improvement = 0.15
        if historical_failures:
            base_improvement += 0.15
        return min(0.50, max(0.05, base_improvement * outcome_score))


adaptive_planner_bridge = AdaptivePlannerBridge()
