"""
JARVIS Product 1.7 - Automation Engine Interfaces.

Defines abstract contracts for Automation Management, Workflow Management, Trigger Listeners, Condition Evaluation, Action Execution, Scheduling, Task Queues, and Notifications.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable, Tuple
from .models import Workflow, WorkflowRunRecord, ConditionConfig, ActionStep, WorkflowStatus, RunStatus


class IWorkflowValidator(ABC):
    @abstractmethod
    def validate_workflow(self, workflow: Workflow) -> Tuple[bool, List[str]]:
        """Returns (is_valid, validation_errors)."""
        pass


class IConditionEvaluator(ABC):
    @abstractmethod
    def evaluate(self, condition: ConditionConfig, context: Dict[str, Any]) -> bool:
        pass


class IActionExecutor(ABC):
    @abstractmethod
    def execute_step(
        self,
        step: ActionStep,
        owner_id: str,
        correlation_id: str,
    ) -> Dict[str, Any]:
        """Executes action step strictly through P1.5 Tool Execution Engine."""
        pass

    @abstractmethod
    def execute_workflow_actions(
        self,
        workflow: Workflow,
        run_record: WorkflowRunRecord,
    ) -> bool:
        pass


class ITriggerListener(ABC):
    @abstractmethod
    def start(self, callback: Callable[[Workflow, Dict[str, Any]], None]) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass


class IScheduler(ABC):
    @abstractmethod
    def start(self) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

    @abstractmethod
    def schedule_workflow(self, workflow: Workflow) -> bool:
        pass

    @abstractmethod
    def unschedule_workflow(self, workflow_id: str) -> bool:
        pass


class ITaskQueue(ABC):
    @abstractmethod
    def push_task(self, workflow: Workflow, trigger_context: Dict[str, Any]) -> str:
        """Returns run_id."""
        pass

    @abstractmethod
    def pop_task(self) -> Optional[Tuple[Workflow, WorkflowRunRecord, Dict[str, Any]]]:
        pass


class IExecutionHistoryStore(ABC):
    @abstractmethod
    def initialize(self) -> None:
        pass

    @abstractmethod
    def save_run_record(self, record: WorkflowRunRecord) -> bool:
        pass

    @abstractmethod
    def get_run_record(self, run_id: str) -> Optional[WorkflowRunRecord]:
        pass

    @abstractmethod
    def list_run_records(
        self,
        workflow_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[WorkflowRunRecord]:
        pass


class INotificationChannel(ABC):
    @abstractmethod
    def send_notification(self, title: str, message: str, level: str = "info") -> bool:
        pass
