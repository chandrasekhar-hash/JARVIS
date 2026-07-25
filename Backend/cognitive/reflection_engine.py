import time
import math
from typing import Dict, List, Optional, Any, Tuple
from cognitive.config import cognitive_config, CognitiveConfig
from cognitive.models import (
    GoalOutcome,
    ReflectionReport,
    CognitiveAssessment,
    WorkflowTemplate,
    FailurePattern,
)
from cognitive.experience_repository import experience_repository, ExperienceRepository
from tools.telemetry import log_structured, backend_log


class PostExecutionReflectionEngine:
    """
    Post-Execution Reflection Engine.
    Operates ONLY after workflow completion to analyze results and generate insights.
    Executes a 9-stage reflection pipeline:
    1. Execution Review
    2. Outcome Comparison
    3. Performance Analysis
    4. Failure Analysis
    5. Success Analysis
    6. Lesson Extraction
    7. Improvement Suggestions
    8. Experience Repository Update
    9. Reflection Report Generation

    MUST NOT execute workflows, modify active plans, or trigger replanning directly.
    """

    def __init__(
        self,
        config: Optional[CognitiveConfig] = None,
        exp_repo: Optional[ExperienceRepository] = None
    ):
        self.config = config or cognitive_config
        self.exp_repo = exp_repo or experience_repository

    async def reflect_on_workflow(
        self,
        goal_id: str,
        workflow_id: str,
        raw_outcome: str,
        total_execution_time_sec: float,
        task_results: Optional[List[Dict[str, Any]]] = None,
        assessment: Optional[CognitiveAssessment] = None,
        errors: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ReflectionReport:
        """
        Executes complete post-execution reflection pipeline and persists insights to ExperienceRepository.
        Returns a structured ReflectionReport.
        """
        start_time = time.time()
        task_list = task_results or []
        err_list = errors or []
        meta_dict = metadata or {}

        # Stage 1: Execution Review
        exec_summary = self._stage1_execution_review(task_list, err_list, total_execution_time_sec)

        # Stage 2: Outcome Comparison
        outcome = self._stage2_outcome_comparison(raw_outcome, exec_summary)

        # Stage 3: Performance Analysis
        tool_scores, bottlenecks = self._stage3_performance_analysis(task_list, total_execution_time_sec)

        # Stage 4: Failure Analysis
        failure_causes, new_failure_patterns = self._stage4_failure_analysis(outcome, err_list, task_list)

        # Stage 5: Success Analysis
        success_factors = self._stage5_success_analysis(outcome, exec_summary, assessment)

        # Stage 6: Lesson Extraction
        lessons = self._stage6_lesson_extraction(outcome, exec_summary, failure_causes, success_factors)

        # Stage 7: Improvement Suggestions & Confidence Adjustment
        improvements, confidence_adj = self._stage7_improvements_and_confidence(outcome, assessment, failure_causes)

        # Stage 8: Experience Repository Updates
        linked_exp_ids, suggested_tmpl_id = await self._stage8_repository_updates(
            goal_id=goal_id,
            outcome=outcome,
            task_list=task_list,
            total_execution_time_sec=total_execution_time_sec,
            new_failure_patterns=new_failure_patterns
        )

        # Stage 9: Report Generation
        report = ReflectionReport(
            goal_id=goal_id or "goal_unknown",
            workflow_id=workflow_id or "wf_unknown",
            outcome=outcome,
            total_execution_time_sec=max(0.0, total_execution_time_sec),
            tool_effectiveness_scores=tool_scores,
            lessons_learned=lessons,
            success_factors=success_factors,
            failure_causes=failure_causes,
            identified_bottlenecks=bottlenecks,
            recommended_improvements=improvements,
            confidence_adjustment=round(confidence_adj, 2),
            execution_statistics={
                "total_tasks": exec_summary["total_tasks"],
                "completed_tasks": exec_summary["completed_tasks"],
                "failed_tasks": exec_summary["failed_tasks"],
                "avg_task_duration": exec_summary["avg_task_duration"]
            },
            linked_experiences=linked_exp_ids,
            suggested_template_id=suggested_tmpl_id
        )

        # Persist ReflectionReport to ExperienceRepository
        try:
            await self.exp_repo.store_reflection(report)
        except Exception as e:
            log_structured(backend_log, "WARNING", f"[ReflectionEngine] Failed to store report in repo: {str(e)}")

        elapsed_ms = (time.time() - start_time) * 1000.0
        log_structured(backend_log, "INFO", f"[ReflectionEngine] Goal '{goal_id}' reflection completed in {elapsed_ms:.1f}ms (Outcome: {outcome.value}, Lessons: {len(lessons)})")

        return report

    # ── Pipeline Stages ──────────────────────────────────────────────────────

    def _stage1_execution_review(self, task_list: List[Dict[str, Any]], err_list: List[str], total_time: float) -> Dict[str, Any]:
        total_tasks = len(task_list)
        completed_tasks = sum(1 for t in task_list if t.get("status") in ("completed", "success", "COMPLETED"))
        failed_tasks = sum(1 for t in task_list if t.get("status") in ("failed", "failure", "FAILED"))

        task_durations = [t.get("duration", 0.0) for t in task_list if t.get("duration") is not None]
        avg_task_duration = (sum(task_durations) / len(task_durations)) if task_durations else 0.0

        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "avg_task_duration": round(avg_task_duration, 2),
            "total_time": total_time,
            "has_errors": len(err_list) > 0 or failed_tasks > 0
        }

    def _stage2_outcome_comparison(self, raw_outcome: str, exec_summary: Dict[str, Any]) -> GoalOutcome:
        normalized = (raw_outcome or "").lower().strip()
        if normalized in ("completed", "success", "succeeded"):
            if exec_summary["failed_tasks"] == 0:
                return GoalOutcome.SUCCESS
            else:
                return GoalOutcome.PARTIAL_SUCCESS
        elif normalized in ("cancelled", "canceled", "aborted", "interrupted"):
            return GoalOutcome.CANCELLED
        elif normalized in ("failed", "failure", "error"):
            if exec_summary["completed_tasks"] > 0:
                return GoalOutcome.PARTIAL_SUCCESS
            return GoalOutcome.FAILED
        else:
            if exec_summary["completed_tasks"] > 0 and exec_summary["failed_tasks"] == 0:
                return GoalOutcome.SUCCESS
            elif exec_summary["completed_tasks"] > 0:
                return GoalOutcome.PARTIAL_SUCCESS
            elif exec_summary["failed_tasks"] > 0:
                return GoalOutcome.FAILED
            return GoalOutcome.CANCELLED

    def _stage3_performance_analysis(self, task_list: List[Dict[str, Any]], total_time: float) -> Tuple[Dict[str, float], List[str]]:
        tool_counts: Dict[str, int] = {}
        tool_successes: Dict[str, int] = {}
        bottlenecks: List[str] = []

        for task in task_list:
            tool_name = task.get("tool_name") or task.get("suggested_tool") or "unknown_tool"
            status = task.get("status", "").lower()
            duration = task.get("duration", 0.0)

            tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
            if status in ("completed", "success", "completed"):
                tool_successes[tool_name] = tool_successes.get(tool_name, 0) + 1

            # Bottleneck detection (> 5.0 seconds or > 40% of total runtime)
            if duration > 5.0 or (total_time > 0 and (duration / total_time) > 0.40):
                bottlenecks.append(f"Task '{task.get('task_name', 'unknown')}' using tool '{tool_name}' took {duration:.2f}s")

        tool_scores: Dict[str, float] = {}
        for tool, total in tool_counts.items():
            succ = tool_successes.get(tool, 0)
            tool_scores[tool] = round(succ / total, 2)

        return tool_scores, bottlenecks

    def _stage4_failure_analysis(
        self,
        outcome: GoalOutcome,
        err_list: List[str],
        task_list: List[Dict[str, Any]]
    ) -> Tuple[List[str], List[FailurePattern]]:
        causes: List[str] = list(err_list)
        new_patterns: List[FailurePattern] = []

        for task in task_list:
            if task.get("status") in ("failed", "failure", "FAILED"):
                err_msg = task.get("error") or task.get("result", {}).get("error") or "Unknown task execution error"
                tool_name = task.get("tool_name", "unknown_tool")
                cause_str = f"Task '{task.get('task_name', 'task')}' failed with tool '{tool_name}': {err_msg}"
                if cause_str not in causes:
                    causes.append(cause_str)

                # Formulate FailurePattern object if error signature is distinct
                sig = f"{tool_name}: {err_msg[:60]}"
                fp = FailurePattern(
                    error_signature=sig,
                    root_cause=err_msg,
                    suggested_workaround=f"Verify parameter schema or check permissions for tool '{tool_name}'"
                )
                new_patterns.append(fp)

        if outcome == GoalOutcome.FAILED and not causes:
            causes.append("Workflow execution terminated prematurely without explicit error output.")

        return causes, new_patterns

    def _stage5_success_analysis(
        self,
        outcome: GoalOutcome,
        exec_summary: Dict[str, Any],
        assessment: Optional[CognitiveAssessment]
    ) -> List[str]:
        factors: List[str] = []
        if outcome in (GoalOutcome.SUCCESS, GoalOutcome.PARTIAL_SUCCESS):
            factors.append(f"Executed {exec_summary['completed_tasks']} tasks successfully.")
            if exec_summary["failed_tasks"] == 0:
                factors.append("100% Task Completion Rate with zero task failures.")
            if assessment and assessment.confidence_score >= 0.80:
                factors.append(f"High pre-execution reasoning confidence ({assessment.confidence_score:.2f}) accurately predicted success.")

        return factors

    def _stage6_lesson_extraction(
        self,
        outcome: GoalOutcome,
        exec_summary: Dict[str, Any],
        causes: List[str],
        factors: List[str]
    ) -> List[str]:
        lessons: List[str] = []

        if outcome == GoalOutcome.SUCCESS:
            lessons.append("Current task DAG decomposition and tool selection were optimal.")
        elif outcome == GoalOutcome.PARTIAL_SUCCESS:
            lessons.append(f"Workflow partially succeeded ({exec_summary['completed_tasks']}/{exec_summary['total_tasks']} tasks completed). Inspect failed steps.")
        else:
            lessons.append(f"Workflow failed. Core root causes: {'; '.join(causes[:2]) if causes else 'Execution error'}.")

        if exec_summary["avg_task_duration"] > 3.0:
            lessons.append(f"Average task duration ({exec_summary['avg_task_duration']}s) is elevated. Consider async tool optimization.")

        return lessons

    def _stage7_improvements_and_confidence(
        self,
        outcome: GoalOutcome,
        assessment: Optional[CognitiveAssessment],
        causes: List[str]
    ) -> Tuple[List[str], float]:
        improvements: List[str] = []
        confidence_adj = 0.0

        if outcome == GoalOutcome.SUCCESS:
            confidence_adj = +0.05
            improvements.append("Retain current strategy pattern as reusable workflow template.")
        elif outcome == GoalOutcome.PARTIAL_SUCCESS:
            confidence_adj = -0.10
            improvements.append("Add explicit error recovery or retry step for failing sub-tasks.")
        elif outcome in (GoalOutcome.FAILED, GoalOutcome.CANCELLED):
            confidence_adj = -0.25
            improvements.append(f"Avoid direct execution for similar goal patterns. Introduce feasibility probing step.")

        if assessment:
            # Overestimation check
            if assessment.confidence_score > 0.80 and outcome == GoalOutcome.FAILED:
                confidence_adj = -0.35
                improvements.append("Pre-execution reasoning significantly overestimated goal feasibility.")

        return improvements, confidence_adj

    async def _stage8_repository_updates(
        self,
        goal_id: str,
        outcome: GoalOutcome,
        task_list: List[Dict[str, Any]],
        total_execution_time_sec: float,
        new_failure_patterns: List[FailurePattern]
    ) -> Tuple[List[str], Optional[str]]:
        linked_ids: List[str] = []
        suggested_tmpl_id: Optional[str] = None

        # 1. Update or create FailurePatterns on failure
        for fp in new_failure_patterns:
            try:
                res_id = await self.exp_repo.store_failure_pattern(fp)
                if res_id:
                    linked_ids.append(res_id)
            except Exception as e:
                log_structured(backend_log, "WARNING", f"[ReflectionEngine] Failed to store FailurePattern: {str(e)}")

        # 2. Store WorkflowTemplate on success
        if outcome == GoalOutcome.SUCCESS and len(task_list) > 0:
            try:
                task_configs = [
                    {"task_name": t.get("task_name", "task"), "suggested_tool": t.get("tool_name") or t.get("suggested_tool")}
                    for t in task_list
                ]
                tmpl = WorkflowTemplate(
                    goal_pattern=f"Goal Pattern {goal_id[:8]}",
                    recommended_tasks=task_configs,
                    success_count=1,
                    average_duration_sec=total_execution_time_sec
                )
                tmpl_id = await self.exp_repo.store_workflow_template(tmpl)
                if tmpl_id:
                    suggested_tmpl_id = tmpl_id
                    linked_ids.append(tmpl_id)
            except Exception as e:
                log_structured(backend_log, "WARNING", f"[ReflectionEngine] Failed to store WorkflowTemplate: {str(e)}")

        return linked_ids, suggested_tmpl_id


post_execution_reflection_engine = PostExecutionReflectionEngine()
