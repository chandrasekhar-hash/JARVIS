import time
from typing import Dict, List, Optional, Set, Any
from brain.event_bus import event_bus
from tools.telemetry import log_structured, backend_log
from autonomous.models import (
    Goal, Task, ExecutionPlan, GoalStatus, ExecutionState, ProgressSnapshot
)
from autonomous.interfaces import IProgressTracker
from autonomous.config import autonomous_config


class ProgressTracker(IProgressTracker):
    """Subsystem responsible for tracking live goal and task execution progress and state transitions."""

    def __init__(self):
        # goal_id -> Goal
        self._goals: Dict[str, Goal] = {}
        # goal_id -> Dict[task_id, Task]
        self._goal_tasks: Dict[str, Dict[str, Task]] = {}
        # goal_id -> Dict[task_id, ExecutionState]
        self._task_states: Dict[str, Dict[str, ExecutionState]] = {}
        # goal_id -> Dict[task_id, float] (start timestamp)
        self._task_start_times: Dict[str, Dict[str, float]] = {}
        # goal_id -> List[float] (completed task durations)
        self._task_durations: Dict[str, List[float]] = {}
        # goal_id -> Dict[task_id, float] (running progress delta 0.0 - 1.0)
        self._task_deltas: Dict[str, Dict[str, float]] = {}

    # ── State Machine Transition Rules ──────────────────────────────────────────

    def _validate_goal_transition(self, current: GoalStatus, target: GoalStatus) -> bool:
        """Validates legal Goal state transitions."""
        if current == target:
            return True

        # Terminal state check
        if current in (GoalStatus.COMPLETED, GoalStatus.FAILED, GoalStatus.CANCELLED):
            return False

        valid_map = {
            GoalStatus.CREATED: {GoalStatus.PLANNING, GoalStatus.IN_PROGRESS, GoalStatus.CANCELLED},
            GoalStatus.PLANNING: {GoalStatus.IN_PROGRESS, GoalStatus.FAILED, GoalStatus.CANCELLED},
            GoalStatus.IN_PROGRESS: {GoalStatus.COMPLETED, GoalStatus.FAILED, GoalStatus.PAUSED, GoalStatus.CANCELLED},
            GoalStatus.PAUSED: {GoalStatus.IN_PROGRESS, GoalStatus.CANCELLED, GoalStatus.FAILED},
        }
        return target in valid_map.get(current, set())

    def _validate_task_transition(self, current: ExecutionState, target: ExecutionState) -> bool:
        """Validates legal Task state transitions."""
        if current == target:
            return True

        # Terminal state check (COMPLETED, SKIPPED, CANCELLED are strictly terminal; FAILED can be retried)
        if current in (ExecutionState.COMPLETED, ExecutionState.SKIPPED, ExecutionState.CANCELLED):
            return False

        valid_map = {
            ExecutionState.PENDING: {
                ExecutionState.RUNNING, 
                ExecutionState.COMPLETED, 
                ExecutionState.FAILED, 
                ExecutionState.CANCELLED, 
                ExecutionState.SKIPPED
            },
            ExecutionState.RUNNING: {
                ExecutionState.COMPLETED, 
                ExecutionState.FAILED, 
                ExecutionState.CANCELLED, 
                ExecutionState.SKIPPED
            },
            ExecutionState.FAILED: {
                ExecutionState.RUNNING,
                ExecutionState.COMPLETED,
                ExecutionState.SKIPPED,
                ExecutionState.CANCELLED
            },
        }
        return target in valid_map.get(current, set())


    # ── Public Progress Management API ──────────────────────────────────────────

    def create_progress(self, goal: Goal, plan: Optional[ExecutionPlan] = None) -> ProgressSnapshot:
        """Initializes progress tracking structures for a new Goal."""
        goal_id = goal.goal_id
        self._goals[goal_id] = goal
        self._goal_tasks[goal_id] = {}
        self._task_states[goal_id] = {}
        self._task_start_times[goal_id] = {}
        self._task_durations[goal_id] = []
        self._task_deltas[goal_id] = {}

        if plan and plan.tasks:
            for t_id, task in plan.tasks.items():
                self._goal_tasks[goal_id][t_id] = task
                self._task_states[goal_id][t_id] = ExecutionState.PENDING
                self._task_deltas[goal_id][t_id] = 0.0

        snapshot = self.get_snapshot(goal_id)
        log_structured(backend_log, "INFO", f"[ProgressTracker] Tracking initialized for Goal {goal_id}.")
        return snapshot

    def update_task_progress(
        self, 
        task_id: str, 
        state: ExecutionState, 
        progress_delta: float = 0.0
    ) -> ProgressSnapshot:
        """
        Updates task state and progress for a task across all active goals.
        Validates state machine rules and computes progress snapshot.
        """
        target_goal_id: Optional[str] = None
        for g_id, t_map in self._goal_tasks.items():
            if task_id in t_map or task_id in self._task_states.get(g_id, {}):
                target_goal_id = g_id
                break

        if not target_goal_id:
            raise ValueError(f"Unknown task_id '{task_id}': Not associated with any tracked goal.")

        return self.update_goal_task_progress(target_goal_id, task_id, state, progress_delta)

    def update_goal_task_progress(
        self, 
        goal_id: str, 
        task_id: str, 
        state: ExecutionState, 
        progress_delta: float = 0.0
    ) -> ProgressSnapshot:
        """Updates task state for a specified goal."""
        if goal_id not in self._goals:
            raise ValueError(f"Unknown goal_id '{goal_id}': Goal is not registered in ProgressTracker.")

        current_state = self._task_states[goal_id].get(task_id, ExecutionState.PENDING)

        # Validate state machine transition
        if not self._validate_task_transition(current_state, state):
            raise ValueError(f"Invalid Task state transition: Cannot transition task '{task_id}' from '{current_state.value}' to '{state.value}'.")

        # Validate progress_delta bounds
        if progress_delta < 0.0 or progress_delta > 1.0:
            raise ValueError(f"Invalid progress_delta '{progress_delta}': Must be between 0.0 and 1.0.")

        now = time.time()
        self._task_states[goal_id][task_id] = state
        self._task_deltas[goal_id][task_id] = progress_delta

        if state == ExecutionState.RUNNING and current_state != ExecutionState.RUNNING:
            self._task_start_times[goal_id][task_id] = now
        elif state == ExecutionState.COMPLETED:
            start = self._task_start_times[goal_id].get(task_id, now)
            duration = max(0.001, now - start)
            self._task_durations[goal_id].append(duration)
            self._task_deltas[goal_id][task_id] = 1.0

        snapshot = self.get_snapshot(goal_id)

        # Broadcast progress events
        event_bus.emit(
            autonomous_config.EVENT_PROGRESS_UPDATED,
            goal_id=goal_id,
            task_id=task_id,
            task_state=state.value,
            overall_progress_pct=snapshot.overall_progress_pct
        )
        event_bus.emit(
            autonomous_config.EVENT_GOAL_PROGRESS_CHANGED,
            goal_id=goal_id,
            overall_progress_pct=snapshot.overall_progress_pct
        )

        return snapshot

    def pause_goal(self, goal_id: str) -> ProgressSnapshot:
        """Transitions goal to PAUSED state."""
        goal = self._goals.get(goal_id)
        if not goal:
            raise ValueError(f"Unknown goal_id '{goal_id}'.")

        if not self._validate_goal_transition(goal.status, GoalStatus.PAUSED):
            raise ValueError(f"Invalid Goal state transition: Cannot pause goal from state '{goal.status.value}'.")

        goal.status = GoalStatus.PAUSED
        goal.updated_at = time.time()

        snapshot = self.get_snapshot(goal_id)
        event_bus.emit(autonomous_config.EVENT_GOAL_PAUSED, goal_id=goal_id)
        event_bus.emit(autonomous_config.EVENT_EXECUTION_PAUSED, goal_id=goal_id)
        return snapshot

    def resume_goal(self, goal_id: str) -> ProgressSnapshot:
        """Transitions goal from PAUSED to IN_PROGRESS."""
        goal = self._goals.get(goal_id)
        if not goal:
            raise ValueError(f"Unknown goal_id '{goal_id}'.")

        if not self._validate_goal_transition(goal.status, GoalStatus.IN_PROGRESS):
            raise ValueError(f"Invalid Goal state transition: Cannot resume goal from state '{goal.status.value}'.")

        goal.status = GoalStatus.IN_PROGRESS
        goal.updated_at = time.time()

        snapshot = self.get_snapshot(goal_id)
        event_bus.emit(autonomous_config.EVENT_GOAL_RESUMED, goal_id=goal_id)
        event_bus.emit(autonomous_config.EVENT_EXECUTION_RESUMED, goal_id=goal_id)
        return snapshot

    def complete_goal(self, goal_id: str, summary: Optional[str] = None) -> ProgressSnapshot:
        """Transitions goal to COMPLETED state."""
        goal = self._goals.get(goal_id)
        if not goal:
            raise ValueError(f"Unknown goal_id '{goal_id}'.")

        if not self._validate_goal_transition(goal.status, GoalStatus.COMPLETED):
            raise ValueError(f"Invalid Goal state transition: Cannot complete goal from state '{goal.status.value}'.")

        goal.status = GoalStatus.COMPLETED
        goal.summary_result = summary or "Goal completed"
        goal.updated_at = time.time()

        snapshot = self.get_snapshot(goal_id)
        event_bus.emit(
            autonomous_config.EVENT_GOAL_COMPLETED,
            goal_id=goal_id,
            duration_seconds=goal.updated_at - goal.created_at,
            summary=goal.summary_result
        )
        return snapshot

    def fail_goal(self, goal_id: str, error: str = "") -> ProgressSnapshot:
        """Transitions goal to FAILED state."""
        goal = self._goals.get(goal_id)
        if not goal:
            raise ValueError(f"Unknown goal_id '{goal_id}'.")

        if not self._validate_goal_transition(goal.status, GoalStatus.FAILED):
            raise ValueError(f"Invalid Goal state transition: Cannot fail goal from state '{goal.status.value}'.")

        goal.status = GoalStatus.FAILED
        goal.summary_result = f"Failed: {error}" if error else "Goal execution failed"
        goal.updated_at = time.time()

        snapshot = self.get_snapshot(goal_id)
        event_bus.emit(autonomous_config.EVENT_GOAL_FAILED, goal_id=goal_id, error=error)
        return snapshot

    def cancel_goal(self, goal_id: str, reason: str = "") -> ProgressSnapshot:
        """Transitions goal to CANCELLED state."""
        goal = self._goals.get(goal_id)
        if not goal:
            raise ValueError(f"Unknown goal_id '{goal_id}'.")

        if not self._validate_goal_transition(goal.status, GoalStatus.CANCELLED):
            raise ValueError(f"Invalid Goal state transition: Cannot cancel goal from state '{goal.status.value}'.")

        goal.status = GoalStatus.CANCELLED
        goal.summary_result = f"Cancelled: {reason}" if reason else "Cancelled"
        goal.updated_at = time.time()

        snapshot = self.get_snapshot(goal_id)
        event_bus.emit(autonomous_config.EVENT_GOAL_CANCELLED, goal_id=goal_id, reason=reason)
        return snapshot

    # ── Snapshot & Metrics Calculation ─────────────────────────────────────────

    def get_snapshot(self, goal_id: str) -> ProgressSnapshot:
        """Calculates live metrics and returns a ProgressSnapshot."""
        goal = self._goals.get(goal_id)
        if not goal:
            raise ValueError(f"Unknown goal_id '{goal_id}'.")

        tasks = self._goal_tasks.get(goal_id, {})
        states = self._task_states.get(goal_id, {})
        deltas = self._task_deltas.get(goal_id, {})

        total_tasks = len(states)
        completed_count = sum(1 for s in states.values() if s == ExecutionState.COMPLETED)
        failed_count = sum(1 for s in states.values() if s == ExecutionState.FAILED)
        running_count = sum(1 for s in states.values() if s == ExecutionState.RUNNING)
        skipped_count = sum(1 for s in states.values() if s == ExecutionState.SKIPPED)
        cancelled_count = sum(1 for s in states.values() if s == ExecutionState.CANCELLED)

        # Progress Calculation
        if goal.status == GoalStatus.COMPLETED:
            overall_pct = 100.0
        elif total_tasks == 0:
            overall_pct = 0.0
        else:
            total_weight = sum(tasks[t_id].weight if t_id in tasks else 1.0 for t_id in states)
            if total_weight <= 0:
                total_weight = float(total_tasks)

            accumulated_weight = 0.0
            for t_id, state in states.items():
                w = tasks[t_id].weight if t_id in tasks else 1.0
                if state in (ExecutionState.COMPLETED, ExecutionState.SKIPPED):
                    accumulated_weight += w
                elif state == ExecutionState.RUNNING:
                    d = deltas.get(t_id, 0.0)
                    accumulated_weight += (w * d)

            overall_pct = (accumulated_weight / total_weight) * 100.0
            overall_pct = max(0.0, min(100.0, overall_pct))

        # ETA Calculation
        durations = self._task_durations.get(goal_id, [])
        remaining_tasks = total_tasks - (completed_count + skipped_count + failed_count + cancelled_count)

        if durations and remaining_tasks > 0:
            avg_duration = sum(durations) / len(durations)
            eta_seconds: Optional[float] = round(avg_duration * remaining_tasks, 2)
        else:
            eta_seconds = None

        return ProgressSnapshot(
            goal_id=goal_id,
            overall_progress_pct=round(overall_pct, 2),
            total_tasks=total_tasks,
            completed_tasks=completed_count,
            failed_tasks=failed_count,
            in_progress_tasks=running_count,
            current_state=goal.status,
            estimated_remaining_seconds=eta_seconds,
            updated_at=time.time()
        )


progress_tracker = ProgressTracker()
