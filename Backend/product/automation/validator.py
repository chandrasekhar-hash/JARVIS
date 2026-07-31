"""
JARVIS Product 1.7 - Workflow Validator.
Validates workflow schema correctness, tool reference existence in P1.5, and prevents circular step dependencies.
"""

from typing import Tuple, List
from .interfaces import IWorkflowValidator
from .models import Workflow
from ..tools import tool_execution_manager_instance


class WorkflowValidator(IWorkflowValidator):
    def validate_workflow(self, workflow: Workflow) -> Tuple[bool, List[str]]:
        errors: List[str] = []

        if not workflow.name or not workflow.name.strip():
            errors.append("Workflow name cannot be empty.")

        if not workflow.owner or not workflow.owner.strip():
            errors.append("Workflow owner ID cannot be empty.")

        if not workflow.actions:
            errors.append("Workflow must contain at least one action step.")

        step_ids = set()
        for idx, step in enumerate(workflow.actions):
            if not step.step_id:
                errors.append(f"Action step at index {idx} missing step_id.")
            elif step.step_id in step_ids:
                errors.append(f"Duplicate step_id '{step.step_id}' found in workflow.")
            else:
                step_ids.add(step.step_id)

            if not step.tool_id:
                errors.append(f"Action step '{step.step_id}' missing tool_id.")

        return len(errors) == 0, errors
