"""
JARVIS Product 1.7 - Workflow Manager.
Orchestrates workflow creation, validation, registration, state transitions, and deletions.
"""

import logging
from typing import List, Dict, Any, Optional
from .models import Workflow, WorkflowStatus, TriggerConfig, ActionStep, ConditionConfig
from .validator import WorkflowValidator
from .registry import WorkflowRegistry
from .logging import automation_logger

logger = logging.getLogger(__name__)


class WorkflowManager:
    def __init__(
        self,
        registry: Optional[WorkflowRegistry] = None,
        validator: Optional[WorkflowValidator] = None,
    ):
        self.registry = registry or WorkflowRegistry()
        self.validator = validator or WorkflowValidator()

    def create_workflow(
        self,
        name: str,
        description: str,
        owner: str,
        trigger: TriggerConfig,
        actions: List[ActionStep],
        conditions: Optional[List[ConditionConfig]] = None,
        tags: Optional[List[str]] = None,
    ) -> Workflow:
        workflow = Workflow.create_new(
            name=name,
            description=description,
            owner=owner,
            trigger=trigger,
            actions=actions,
            conditions=conditions,
            tags=tags,
        )

        is_valid, errors = self.validator.validate_workflow(workflow)
        if not is_valid:
            raise ValueError(f"Workflow validation failed: {', '.join(errors)}")

        self.registry.register_workflow(workflow)
        automation_logger.log_event(
            event_name="WORKFLOW_CREATED",
            user_id=owner,
            workflow_id=workflow.workflow_id,
            details={"name": name, "actions_count": len(actions)},
        )
        return workflow

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        return self.registry.get_workflow(workflow_id)

    def list_workflows(self, owner_id: Optional[str] = None) -> List[Workflow]:
        return self.registry.list_workflows(owner_id=owner_id)

    def pause_workflow(self, workflow_id: str, user_id: str) -> bool:
        wf = self.registry.get_workflow(workflow_id)
        if not wf:
            return False
        wf.status = WorkflowStatus.PAUSED
        self.registry.register_workflow(wf)
        automation_logger.log_event("WORKFLOW_PAUSED", user_id, workflow_id)
        return True

    def resume_workflow(self, workflow_id: str, user_id: str) -> bool:
        wf = self.registry.get_workflow(workflow_id)
        if not wf:
            return False
        wf.status = WorkflowStatus.ACTIVE
        self.registry.register_workflow(wf)
        automation_logger.log_event("WORKFLOW_RESUMED", user_id, workflow_id)
        return True

    def delete_workflow(self, workflow_id: str, user_id: str) -> bool:
        wf = self.registry.get_workflow(workflow_id)
        if not wf:
            return False
        success = self.registry.delete_workflow(workflow_id)
        if success:
            automation_logger.log_event("WORKFLOW_DELETED", user_id, workflow_id)
        return success
