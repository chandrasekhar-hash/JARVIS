import time
from typing import List, Dict, Set, Optional, Any
from brain.event_bus import event_bus
from tools.telemetry import log_structured, backend_log
from autonomous.models import Task, ExecutionPlan
from autonomous.interfaces import IExecutionPlanner


class ExecutionPlanner(IExecutionPlanner):
    """Subsystem responsible for converting Task lists into validated execution DAGs."""

    def build_execution_plan(self, tasks: List[Task]) -> ExecutionPlan:
        """Converts a list of Task objects into a structured ExecutionPlan DAG."""
        plan_tasks: Dict[str, Task] = {}
        dag_edges: Dict[str, List[str]] = {}

        for task in tasks:
            plan_tasks[task.task_id] = task
            dag_edges[task.task_id] = list(task.dependencies)

        plan = ExecutionPlan(
            goal_id=tasks[0].goal_id if tasks else "unknown_goal",
            tasks=plan_tasks,
            dag_edges=dag_edges,
            created_at=time.time()
        )

        log_structured(
            backend_log,
            "INFO",
            f"[ExecutionPlanner] Built execution plan {plan.plan_id} with {len(tasks)} tasks."
        )
        return plan

    def validate_plan(self, plan: ExecutionPlan) -> bool:
        """Validates that all dependencies exist and that the graph contains no cycles."""
        tasks = plan.tasks
        dag = plan.dag_edges

        # 1. Validate existence of referenced dependencies
        for task_id, deps in dag.items():
            if task_id not in tasks:
                log_structured(backend_log, "WARNING", f"[ExecutionPlanner] Task '{task_id}' missing in task map.")
                return False
            for dep_id in deps:
                if dep_id not in tasks:
                    log_structured(backend_log, "WARNING", f"[ExecutionPlanner] Task '{task_id}' depends on missing task '{dep_id}'.")
                    return False

        # 2. Cycle Detection using DFS 3-Coloring (0=UNVISITED, 1=VISITING, 2=VISITED)
        UNVISITED, VISITING, VISITED = 0, 1, 2
        node_states: Dict[str, int] = {t_id: UNVISITED for t_id in tasks}

        def has_cycle(node: str) -> bool:
            node_states[node] = VISITING
            for dep in dag.get(node, []):
                if node_states[dep] == VISITING:
                    log_structured(backend_log, "WARNING", f"[ExecutionPlanner] Cycle detected: {node} -> {dep}")
                    return True
                if node_states[dep] == UNVISITED:
                    if has_cycle(dep):
                        return True
            node_states[node] = VISITED
            return False

        for task_id in tasks:
            if node_states[task_id] == UNVISITED:
                if has_cycle(task_id):
                    return False

        return True

    def get_topological_order(self, plan: ExecutionPlan) -> List[str]:
        """Returns task IDs in topologically sorted execution order."""
        if not self.validate_plan(plan):
            raise ValueError(f"Cannot topologically sort invalid or cyclic plan: {plan.plan_id}")

        # Kahn's Algorithm for Topological Sort
        in_degree: Dict[str, int] = {t_id: 0 for t_id in plan.tasks}
        # Build adjacency graph (parent -> children who depend on parent)
        adj: Dict[str, List[str]] = {t_id: [] for t_id in plan.tasks}

        for task_id, deps in plan.dag_edges.items():
            in_degree[task_id] = len(deps)
            for dep in deps:
                if dep not in adj:
                    adj[dep] = []
                adj[dep].append(task_id)

        queue: List[str] = [t_id for t_id, deg in in_degree.items() if deg == 0]
        sorted_order: List[str] = []

        while queue:
            curr = queue.pop(0)
            sorted_order.append(curr)
            for child in adj.get(curr, []):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        if len(sorted_order) != len(plan.tasks):
            raise ValueError("Topological sort failed: graph contains cycle.")

        return sorted_order

    def get_execution_batches(self, plan: ExecutionPlan) -> List[List[str]]:
        """Groups tasks into parallel execution batches based on dependency depth."""
        if not self.validate_plan(plan):
            raise ValueError(f"Cannot compute execution batches for invalid plan: {plan.plan_id}")

        batches: List[List[str]] = []
        completed: Set[str] = set()
        remaining: Set[str] = set(plan.tasks.keys())

        while remaining:
            # Ready batch: tasks in remaining whose dependencies are all in completed
            batch = [
                t_id for t_id in remaining 
                if all(dep in completed for dep in plan.dag_edges.get(t_id, []))
            ]

            if not batch:
                raise ValueError("Execution batching deadlocked: potential cycle in DAG edges.")

            batches.append(batch)
            for t_id in batch:
                completed.add(t_id)
                remaining.remove(t_id)

        return batches

    def get_ready_tasks(self, plan: ExecutionPlan, completed_tasks: List[str]) -> List[Task]:
        """Returns ready tasks whose dependencies are satisfied and are not yet completed."""
        completed_set = set(completed_tasks)
        ready: List[Task] = []

        for task_id, task in plan.tasks.items():
            if task_id not in completed_set:
                deps = plan.dag_edges.get(task_id, [])
                if all(d in completed_set for d in deps):
                    ready.append(task)

        return ready

    def mark_task_complete(self, plan: ExecutionPlan, task_id: str) -> None:
        """Marks a task as completed in plan metadata."""
        if task_id in plan.tasks:
            log_structured(backend_log, "INFO", f"[ExecutionPlanner] Task {task_id} marked complete in plan {plan.plan_id}.")

    def mark_task_failed(self, plan: ExecutionPlan, task_id: str) -> None:
        """Marks a task as failed in plan metadata."""
        if task_id in plan.tasks:
            log_structured(backend_log, "WARNING", f"[ExecutionPlanner] Task {task_id} marked failed in plan {plan.plan_id}.")


execution_planner = ExecutionPlanner()
