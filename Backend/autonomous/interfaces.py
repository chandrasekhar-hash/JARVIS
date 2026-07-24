from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from autonomous.models import (
    Goal, Task, ExecutionPlan, TaskResult, ExecutionState, 
    ProgressSnapshot, RecoveryAttempt, WorkflowCheckpoint
)


class IGoalManager(ABC):
    @abstractmethod
    async def create_goal(self, user_intent: str, metadata: Optional[Dict[str, Any]] = None) -> Goal:
        pass

    @abstractmethod
    async def cancel_goal(self, goal_id: str, reason: str = "") -> bool:
        pass

    @abstractmethod
    async def pause_goal(self, goal_id: str) -> bool:
        pass

    @abstractmethod
    async def resume_goal(self, goal_id: str) -> bool:
        pass

    @abstractmethod
    async def get_goal_status(self, goal_id: str) -> Optional[Goal]:
        pass

    @abstractmethod
    async def list_goals(self, status: Optional[str] = None, limit: int = 20) -> List[Goal]:
        pass


class ITaskPlanner(ABC):
    @abstractmethod
    async def plan_tasks(self, goal: Goal, context: Optional[Dict[str, Any]] = None) -> List[Task]:
        pass

    @abstractmethod
    async def replan_subgraph(self, goal: Goal, failed_task: Task, error_context: str) -> List[Task]:
        pass


class IExecutionPlanner(ABC):
    @abstractmethod
    def build_execution_plan(self, tasks: List[Task]) -> ExecutionPlan:
        pass

    @abstractmethod
    def get_ready_tasks(self, plan: ExecutionPlan, completed_task_ids: List[str]) -> List[Task]:
        pass


class IToolSelector(ABC):
    @abstractmethod
    async def select_tool_for_task(self, task: Task, runtime_context: Dict[str, Any]) -> Dict[str, Any]:
        pass


class IExecutionEngine(ABC):
    @abstractmethod
    async def execute_task(self, task: Task, selected_tool: Dict[str, Any]) -> TaskResult:
        pass

    @abstractmethod
    async def cancel_task(self, task_id: str) -> bool:
        pass


class IFailureRecoveryEngine(ABC):
    @abstractmethod
    async def evaluate_and_recover(self, task: Task, result: TaskResult, plan: ExecutionPlan) -> RecoveryAttempt:
        pass


class IProgressTracker(ABC):
    @abstractmethod
    def update_task_progress(self, task_id: str, state: ExecutionState, progress_delta: float) -> ProgressSnapshot:
        pass

    @abstractmethod
    def get_snapshot(self, goal_id: str) -> ProgressSnapshot:
        pass


class IWorkflowManager(ABC):
    @abstractmethod
    async def save_checkpoint(self, plan: ExecutionPlan, state_data: Dict[str, Any]) -> WorkflowCheckpoint:
        pass

    @abstractmethod
    async def resume_workflow(self, workflow_id: str) -> ExecutionPlan:
        pass


class IActionHistory(ABC):
    @abstractmethod
    async def log_action(self, task: Task, result: TaskResult, recovery: Optional[RecoveryAttempt] = None) -> None:
        pass

    @abstractmethod
    async def get_goal_history(self, goal_id: str) -> List[Dict[str, Any]]:
        pass
