import time
from typing import Dict, List, Optional, Any, Set, Tuple
from cognitive.config import cognitive_config, CognitiveConfig
from cognitive.models import (
    StrategyType,
    RiskLevel,
    CognitiveAssessment,
    AdaptationPlan,
    GoalExecutionPlan,
)
from cognitive.policy_engine import cognitive_policy_engine, CognitivePolicyEngine
from cognitive.experience_repository import experience_repository, ExperienceRepository
from tools.telemetry import log_structured, backend_log


class MultiGoalCoordinator:
    """
    Multi-Goal Coordinator & Cognitive Goal Arbitration.
    Intelligently coordinates multiple concurrent goals and produces an optimized, non-conflicting execution schedule.
    Executes a 9-stage coordination pipeline:
    1. Goal Collection
    2. Priority Scoring
    3. Dependency Detection
    4. Resource Conflict Analysis
    5. Policy Validation
    6. Execution Scheduling
    7. Parallel Batch Generation
    8. Deadlock / Conflict Check
    9. GoalExecutionPlan Output

    MUST NOT execute workflows, modify runtime schedulers, or perform reflection directly.
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

    async def coordinate_goals(
        self,
        assessments: List[CognitiveAssessment],
        adaptation_plans: Optional[List[AdaptationPlan]] = None,
        user_priorities: Optional[Dict[str, float]] = None,
        resource_metadata: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> GoalExecutionPlan:
        """
        Executes complete multi-goal coordination pipeline.
        Returns a structured GoalExecutionPlan.
        """
        start_time = time.time()
        assessments_list = assessments or []
        adaptations = {ap.goal_id: ap for ap in (adaptation_plans or [])}
        priorities_input = user_priorities or {}
        resource_meta = resource_metadata or {}

        # Stage 1: Goal Collection
        valid_assessments, unapproved_blocked = self._stage1_goal_collection(assessments_list)

        # Stage 2: Priority Scoring
        priority_scores = self._stage2_priority_scoring(valid_assessments, priorities_input)

        # Stage 3: Dependency Detection
        dep_graph, circular_blocked = self._stage3_dependency_detection(valid_assessments)

        # Stage 4: Resource Conflict Analysis
        resource_allocations, conflict_blocked = self._stage4_resource_conflict_analysis(valid_assessments, resource_meta)

        # Combine all blocked goals
        blocked_goals = list(set(unapproved_blocked + circular_blocked + conflict_blocked))

        # Stage 5: Policy Validation & Resource Limit Enforcer
        policy_blocked = self._stage5_policy_validation(valid_assessments, blocked_goals)
        blocked_goals = list(set(blocked_goals + policy_blocked))

        # Filter active schedulable goals
        active_goals = [a for a in valid_assessments if a.goal_id not in blocked_goals]

        # Stage 6: Execution Scheduling
        ordered_goals = self._stage6_execution_scheduling(active_goals, priority_scores, dep_graph)

        # Stage 7: Parallel Batch Generation
        batches = self._stage7_parallel_batch_generation(ordered_goals, dep_graph, resource_allocations)

        # Stage 8: Deadlock / Conflict Check
        has_deadlock, deadlock_notes = self._stage8_deadlock_check(batches, dep_graph)

        # Stage 9: GoalExecutionPlan Output
        summary = (
            f"Coordinated {len(assessments_list)} goals. "
            f"Scheduled {len(ordered_goals)} active goals into {len(batches)} parallel batches. "
            f"Blocked goals: {len(blocked_goals)}. "
            f"{'Zero deadlocks detected.' if not has_deadlock else deadlock_notes}"
        )

        plan = GoalExecutionPlan(
            ordered_goals=ordered_goals,
            priority_scores=priority_scores,
            dependency_graph=dep_graph,
            execution_batches=batches,
            blocked_goals=blocked_goals,
            resource_allocations=resource_allocations,
            estimated_completion_order=ordered_goals,
            coordination_summary=summary,
            approved=not has_deadlock
        )

        elapsed_ms = (time.time() - start_time) * 1000.0
        log_structured(backend_log, "INFO", f"[MultiGoalCoordinator] Coordinated {len(assessments_list)} goals in {elapsed_ms:.1f}ms ({len(batches)} batches, {len(blocked_goals)} blocked)")

        return plan

    # ── Pipeline Stages ──────────────────────────────────────────────────────

    def _stage1_goal_collection(self, assessments: List[CognitiveAssessment]) -> Tuple[List[CognitiveAssessment], List[str]]:
        valid: List[CognitiveAssessment] = []
        blocked: List[str] = []

        for a in assessments:
            if not a.approved:
                blocked.append(a.goal_id)
            else:
                valid.append(a)

        return valid, blocked

    def _stage2_priority_scoring(self, assessments: List[CognitiveAssessment], user_priorities: Dict[str, float]) -> Dict[str, float]:
        scores: Dict[str, float] = {}

        for a in assessments:
            # 1. Base user priority if present (0.0 to 1.0)
            base_prio = user_priorities.get(a.goal_id, 0.50)

            # 2. Confidence bonus
            conf_bonus = a.confidence_score * 0.25

            # 3. Risk weighting (Higher risk = higher priority or required focus)
            risk_bonus = 0.05
            if a.risk_level == RiskLevel.CRITICAL:
                risk_bonus = 0.20
            elif a.risk_level == RiskLevel.HIGH:
                risk_bonus = 0.15
            elif a.risk_level == RiskLevel.MEDIUM:
                risk_bonus = 0.10

            # 4. Complexity adjustment (Prefer quick wins for equal priority)
            complexity_penalty = (a.estimated_complexity / 10.0) * 0.10

            total_score = (base_prio * 0.50) + conf_bonus + risk_bonus - complexity_penalty
            scores[a.goal_id] = round(max(0.01, min(1.0, total_score)), 2)

        return scores

    def _stage3_dependency_detection(self, assessments: List[CognitiveAssessment]) -> Tuple[Dict[str, List[str]], List[str]]:
        dep_graph: Dict[str, List[str]] = {}
        circular_blocked: List[str] = []

        # Build adjacency graph
        goal_ids = {a.goal_id for a in assessments}
        for a in assessments:
            # Check reasoning summary or matched experience IDs for explicit dependencies
            deps = []
            if hasattr(a, "metadata") and isinstance(a.metadata, dict):
                deps = a.metadata.get("depends_on", [])
            dep_graph[a.goal_id] = [d for d in deps if d in goal_ids]

        # Detect cycles using Tarjan / DFS
        visited: Dict[str, int] = {}  # 0: unvisited, 1: visiting, 2: visited

        def dfs(node: str, path: List[str]) -> bool:
            visited[node] = 1
            path.append(node)
            for neighbor in dep_graph.get(node, []):
                if visited.get(neighbor, 0) == 1:
                    # Cycle detected!
                    circular_blocked.extend(path[path.index(neighbor):])
                    return True
                elif visited.get(neighbor, 0) == 0:
                    if dfs(neighbor, path):
                        return True
            visited[node] = 2
            path.pop()
            return False

        for gid in goal_ids:
            if visited.get(gid, 0) == 0:
                dfs(gid, [])

        return dep_graph, list(set(circular_blocked))

    def _stage4_resource_conflict_analysis(
        self,
        assessments: List[CognitiveAssessment],
        resource_meta: Dict[str, Any]
    ) -> Tuple[Dict[str, List[str]], List[str]]:
        allocations: Dict[str, List[str]] = {}
        blocked: List[str] = []

        resource_usage: Dict[str, List[str]] = {}

        for a in assessments:
            # Estimate resources used from reasoning summary and strategy
            res_list: List[str] = []
            text = a.reasoning_summary.lower()

            if "file" in text or "folder" in text or "directory" in text:
                res_list.append("fs_lock")
            if "browser" in text or "url" in text or "search" in text:
                res_list.append("browser_lock")
            if "system" in text or "app" in text:
                res_list.append("system_app_lock")

            allocations[a.goal_id] = res_list

            for res in res_list:
                resource_usage.setdefault(res, []).append(a.goal_id)

        # Detect exclusive lock conflicts
        for res, users in resource_usage.items():
            if len(users) > 1 and res == "fs_lock":
                # Multiple write goals accessing filesystem -> Block lowest priority/high risk
                log_structured(backend_log, "WARNING", f"[MultiGoalCoordinator] Shared resource contention on '{res}' between {users}")

        return allocations, blocked

    def _stage5_policy_validation(self, assessments: List[CognitiveAssessment], current_blocked: List[str]) -> List[str]:
        policy_blocked: List[str] = []
        active_count = len(assessments) - len(current_blocked)

        # Enforce MAX_CONCURRENT_GOALS
        if active_count > self.config.MAX_CONCURRENT_GOALS:
            excess = active_count - self.config.MAX_CONCURRENT_GOALS
            log_structured(backend_log, "WARNING", f"[MultiGoalCoordinator] Active goals ({active_count}) exceed MAX_CONCURRENT_GOALS ({self.config.MAX_CONCURRENT_GOALS}). Blocking {excess} goals.")
            
            # Sort by confidence/risk to block lowest ranking goals
            sorted_assessments = sorted(assessments, key=lambda x: x.confidence_score)
            for a in sorted_assessments:
                if a.goal_id not in current_blocked and len(policy_blocked) < excess:
                    policy_blocked.append(a.goal_id)

        return policy_blocked

    def _stage6_execution_scheduling(
        self,
        active_goals: List[CognitiveAssessment],
        priorities: Dict[str, float],
        dep_graph: Dict[str, List[str]]
    ) -> List[str]:
        # Topological sort weighted by priority score
        in_degree: Dict[str, int] = {a.goal_id: 0 for a in active_goals}
        active_ids = set(in_degree.keys())

        for gid, deps in dep_graph.items():
            if gid in active_ids:
                for dep in deps:
                    if dep in active_ids:
                        in_degree[gid] += 1

        # Queue nodes with zero in-degree, sorted by priority score descending
        ready_queue = [gid for gid, deg in in_degree.items() if deg == 0]
        ready_queue.sort(key=lambda x: priorities.get(x, 0.0), reverse=True)

        ordered: List[str] = []
        while ready_queue:
            curr = ready_queue.pop(0)
            ordered.append(curr)

            # Reduce in-degree for dependents
            for gid, deps in dep_graph.items():
                if gid in active_ids and curr in deps:
                    in_degree[gid] -= 1
                    if in_degree[gid] == 0 and gid not in ordered and gid not in ready_queue:
                        ready_queue.append(gid)
                        ready_queue.sort(key=lambda x: priorities.get(x, 0.0), reverse=True)

        # Append any remaining active goals not caught by topo sort
        for a in active_goals:
            if a.goal_id not in ordered:
                ordered.append(a.goal_id)

        return ordered

    def _stage7_parallel_batch_generation(
        self,
        ordered_goals: List[str],
        dep_graph: Dict[str, List[str]],
        allocations: Dict[str, List[str]]
    ) -> List[List[str]]:
        if not ordered_goals:
            return []

        batches: List[List[str]] = []
        current_batch: List[str] = []
        current_resources: Set[str] = set()

        for gid in ordered_goals:
            deps = dep_graph.get(gid, [])
            res_needed = set(allocations.get(gid, []))

            # Goal cannot be in current batch if it depends on a goal in current batch or shares conflicting resource
            has_dep_in_batch = any(d in current_batch for d in deps)
            has_res_conflict = bool(current_resources.intersection(res_needed)) and ("fs_lock" in res_needed or "system_app_lock" in res_needed)

            if current_batch and (has_dep_in_batch or has_res_conflict):
                batches.append(current_batch)
                current_batch = [gid]
                current_resources = res_needed
            else:
                current_batch.append(gid)
                current_resources.update(res_needed)

        if current_batch:
            batches.append(current_batch)

        return batches

    def _stage8_deadlock_check(self, batches: List[List[str]], dep_graph: Dict[str, List[str]]) -> Tuple[bool, str]:
        # Verify no goal in batch N depends on a goal in batch M (where M >= N)
        goal_to_batch: Dict[str, int] = {}
        for b_idx, batch in enumerate(batches):
            for gid in batch:
                goal_to_batch[gid] = b_idx

        for gid, deps in dep_graph.items():
            b_gid = goal_to_batch.get(gid)
            if b_gid is None:
                continue
            for dep in deps:
                b_dep = goal_to_batch.get(dep)
                if b_dep is not None and b_dep >= b_gid:
                    return True, f"Deadlock: Goal '{gid}' in batch {b_gid} depends on '{dep}' in batch {b_dep}"

        return False, "No deadlocks detected."


multi_goal_coordinator = MultiGoalCoordinator()
