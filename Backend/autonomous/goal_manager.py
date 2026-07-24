import time
from typing import Dict, List, Optional, Any
from brain.event_bus import event_bus
from tools.telemetry import log_structured, backend_log
from autonomous.models import Goal, GoalStatus
from autonomous.interfaces import IGoalManager
from autonomous.config import autonomous_config


class GoalManager(IGoalManager):
    """Subsystem responsible for managing high-level user goal lifecycles."""

    def __init__(self):
        self._goals: Dict[str, Goal] = {}

    async def create_goal(self, user_intent: str, metadata: Optional[Dict[str, Any]] = None) -> Goal:
        """Creates and registers a new high-level user goal."""
        goal = Goal(
            user_intent=user_intent,
            status=GoalStatus.CREATED,
            metadata=metadata or {},
            created_at=time.time(),
            updated_at=time.time()
        )
        self._goals[goal.goal_id] = goal

        log_structured(
            backend_log, 
            "INFO", 
            f"[GoalManager] Goal created: '{goal.user_intent}' (ID: {goal.goal_id})"
        )

        event_bus.emit(
            autonomous_config.EVENT_GOAL_CREATED,
            goal_id=goal.goal_id,
            user_intent=goal.user_intent,
            created_at=goal.created_at
        )

        return goal

    async def start_goal(self, goal_id: str) -> bool:
        """Transitions goal status to IN_PROGRESS and emits GoalStarted event."""
        goal = self._goals.get(goal_id)
        if not goal:
            log_structured(backend_log, "WARNING", f"[GoalManager] Cannot start missing goal: {goal_id}")
            return False

        goal.status = GoalStatus.IN_PROGRESS
        goal.updated_at = time.time()

        event_bus.emit(
            autonomous_config.EVENT_GOAL_STARTED,
            goal_id=goal.goal_id,
            user_intent=goal.user_intent,
            started_at=goal.updated_at
        )
        return True

    async def complete_goal(self, goal_id: str, summary: Optional[str] = None) -> bool:
        """Transitions goal status to COMPLETED and records summary result."""
        goal = self._goals.get(goal_id)
        if not goal:
            return False

        goal.status = GoalStatus.COMPLETED
        goal.summary_result = summary or "Goal completed successfully."
        goal.updated_at = time.time()

        event_bus.emit(
            autonomous_config.EVENT_GOAL_COMPLETED,
            goal_id=goal.goal_id,
            duration_seconds=goal.updated_at - goal.created_at,
            summary=goal.summary_result
        )
        return True

    async def fail_goal(self, goal_id: str, error: str) -> bool:
        """Transitions goal status to FAILED and records error message."""
        goal = self._goals.get(goal_id)
        if not goal:
            return False

        goal.status = GoalStatus.FAILED
        goal.summary_result = f"Failed: {error}"
        goal.updated_at = time.time()

        event_bus.emit(
            autonomous_config.EVENT_GOAL_FAILED,
            goal_id=goal.goal_id,
            error=error
        )
        return True

    async def cancel_goal(self, goal_id: str, reason: str = "") -> bool:
        """Cancels an active or pending goal."""
        goal = self._goals.get(goal_id)
        if not goal or goal.status in (GoalStatus.COMPLETED, GoalStatus.CANCELLED):
            return False

        goal.status = GoalStatus.CANCELLED
        goal.summary_result = f"Cancelled: {reason}" if reason else "Cancelled by user"
        goal.updated_at = time.time()

        log_structured(backend_log, "INFO", f"[GoalManager] Goal cancelled: {goal_id} ({reason})")

        event_bus.emit(
            autonomous_config.EVENT_GOAL_CANCELLED,
            goal_id=goal.goal_id,
            reason=reason,
            cancelled_at=goal.updated_at
        )
        return True

    async def pause_goal(self, goal_id: str) -> bool:
        """Pauses execution for a goal in progress."""
        goal = self._goals.get(goal_id)
        if not goal or goal.status != GoalStatus.IN_PROGRESS:
            return False

        goal.status = GoalStatus.PAUSED
        goal.updated_at = time.time()

        event_bus.emit(
            autonomous_config.EVENT_EXECUTION_PAUSED,
            goal_id=goal.goal_id,
            paused_at=goal.updated_at
        )
        return True

    async def resume_goal(self, goal_id: str) -> bool:
        """Resumes a paused goal."""
        goal = self._goals.get(goal_id)
        if not goal or goal.status != GoalStatus.PAUSED:
            return False

        goal.status = GoalStatus.IN_PROGRESS
        goal.updated_at = time.time()

        event_bus.emit(
            autonomous_config.EVENT_EXECUTION_RESUMED,
            goal_id=goal.goal_id,
            resumed_at=goal.updated_at
        )
        return True

    async def get_goal_status(self, goal_id: str) -> Optional[Goal]:
        """Returns the current Goal object or None if not found."""
        return self._goals.get(goal_id)

    async def list_goals(self, status: Optional[str] = None, limit: int = 20) -> List[Goal]:
        """Lists registered goals filtered by status with limit."""
        goals = list(self._goals.values())
        if status:
            goals = [g for g in goals if g.status.value == status or g.status == status]
        return goals[:limit]


goal_manager = GoalManager()
