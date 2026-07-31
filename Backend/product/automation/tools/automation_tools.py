"""
JARVIS Product 1.7 - Automation Engine Tool Registrations for P1.5 Tool Execution Engine.
Registers automation tools (`automation_create_workflow`, `automation_trigger_workflow`, `automation_pause_workflow`, `automation_resume_workflow`, `automation_delete_workflow`, `automation_list_workflows`, `automation_get_history`).
"""

import logging
from typing import Dict, Any, List
from ...tools.models import ToolMetadata, ToolCategory, ToolCapability
from ..automation_engine import automation_manager_instance
from ..models import TriggerConfig, ActionStep, ConditionConfig, TriggerType

logger = logging.getLogger(__name__)


def handle_automation_create_workflow(
    name: str,
    description: str,
    user_id: str = "default_user",
    trigger_type: str = "MANUAL",
    actions: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    trig_cfg = TriggerConfig(trigger_type=TriggerType(trigger_type.upper()))
    act_steps = [ActionStep.from_dict(a) for a in (actions or [])]

    wf = automation_manager_instance.create_workflow(
        name=name,
        description=description,
        owner=user_id,
        trigger=trig_cfg,
        actions=act_steps,
    )
    return {
        "status": "success",
        "workflow_id": wf.workflow_id,
        "name": wf.name,
        "actions_count": len(wf.actions),
    }


def handle_automation_trigger_workflow(workflow_id: str, user_id: str = "default_user") -> Dict[str, Any]:
    run_id = automation_manager_instance.trigger_workflow_manually(workflow_id=workflow_id)
    return {
        "status": "success",
        "workflow_id": workflow_id,
        "run_id": run_id,
    }


def handle_automation_pause_workflow(workflow_id: str, user_id: str = "default_user") -> Dict[str, Any]:
    success = automation_manager_instance.pause_workflow(workflow_id=workflow_id, user_id=user_id)
    return {
        "status": "success" if success else "failed",
        "workflow_id": workflow_id,
        "paused": success,
    }


def handle_automation_resume_workflow(workflow_id: str, user_id: str = "default_user") -> Dict[str, Any]:
    success = automation_manager_instance.resume_workflow(workflow_id=workflow_id, user_id=user_id)
    return {
        "status": "success" if success else "failed",
        "workflow_id": workflow_id,
        "resumed": success,
    }


def handle_automation_delete_workflow(workflow_id: str, user_id: str = "default_user") -> Dict[str, Any]:
    success = automation_manager_instance.delete_workflow(workflow_id=workflow_id, user_id=user_id)
    return {
        "status": "success" if success else "failed",
        "workflow_id": workflow_id,
        "deleted": success,
    }


def handle_automation_list_workflows(user_id: str = "default_user") -> Dict[str, Any]:
    workflows = automation_manager_instance.list_workflows(owner_id=user_id)
    return {
        "status": "success",
        "count": len(workflows),
        "workflows": [
            {
                "workflow_id": wf.workflow_id,
                "name": wf.name,
                "status": wf.status.value,
                "trigger_type": wf.trigger.trigger_type.value,
                "actions_count": len(wf.actions),
            }
            for wf in workflows
        ],
    }


def handle_automation_get_history(workflow_id: str = None, user_id: str = "default_user") -> Dict[str, Any]:
    runs = automation_manager_instance.list_execution_history(workflow_id=workflow_id, owner_id=user_id)
    return {
        "status": "success",
        "runs_count": len(runs),
        "runs": [
            {
                "run_id": r.run_id,
                "workflow_id": r.workflow_id,
                "status": r.status.value,
                "steps_completed": r.steps_completed,
                "total_steps": r.total_steps,
                "duration_ms": r.duration_ms,
            }
            for r in runs
        ],
    }


def get_automation_tool_metadatas() -> List[ToolMetadata]:
    return [
        ToolMetadata(
            tool_id="automation_create_workflow",
            name="Create Automation Workflow",
            description="Creates and registers a new automated workflow pipeline in the JARVIS Automation Engine.",
            category=ToolCategory.AUTOMATION,
            capabilities=[ToolCapability.FILESYSTEM_WRITE.value],
            safety_level="safe",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "user_id": {"type": "string", "default": "default_user"},
                    "trigger_type": {"type": "string", "default": "MANUAL"},
                    "actions": {"type": "array"},
                },
                "required": ["name", "description", "actions"],
            },
            handler=handle_automation_create_workflow,
        ),
        ToolMetadata(
            tool_id="automation_trigger_workflow",
            name="Trigger Automation Workflow",
            description="Manually triggers immediate execution of an automated workflow.",
            category=ToolCategory.AUTOMATION,
            capabilities=[ToolCapability.SYSTEM_EXECUTE.value],
            safety_level="safe",
            input_schema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string"},
                    "user_id": {"type": "string", "default": "default_user"},
                },
                "required": ["workflow_id"],
            },
            handler=handle_automation_trigger_workflow,
        ),
        ToolMetadata(
            tool_id="automation_pause_workflow",
            name="Pause Automation Workflow",
            description="Pauses an active workflow schedule.",
            category=ToolCategory.AUTOMATION,
            capabilities=[ToolCapability.SYSTEM_EXECUTE.value],
            safety_level="safe",
            input_schema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string"},
                    "user_id": {"type": "string", "default": "default_user"},
                },
                "required": ["workflow_id"],
            },
            handler=handle_automation_pause_workflow,
        ),
        ToolMetadata(
            tool_id="automation_resume_workflow",
            name="Resume Automation Workflow",
            description="Resumes a paused workflow schedule.",
            category=ToolCategory.AUTOMATION,
            capabilities=[ToolCapability.SYSTEM_EXECUTE.value],
            safety_level="safe",
            input_schema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string"},
                    "user_id": {"type": "string", "default": "default_user"},
                },
                "required": ["workflow_id"],
            },
            handler=handle_automation_resume_workflow,
        ),
        ToolMetadata(
            tool_id="automation_delete_workflow",
            name="Delete Automation Workflow",
            description="Deletes a registered automation workflow.",
            category=ToolCategory.AUTOMATION,
            capabilities=[ToolCapability.FILESYSTEM_WRITE.value],
            safety_level="confirmation_required",
            input_schema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string"},
                    "user_id": {"type": "string", "default": "default_user"},
                },
                "required": ["workflow_id"],
            },
            handler=handle_automation_delete_workflow,
        ),
        ToolMetadata(
            tool_id="automation_list_workflows",
            name="List Automation Workflows",
            description="Lists all registered automation workflows and their statuses.",
            category=ToolCategory.AUTOMATION,
            capabilities=[ToolCapability.READ_ONLY.value],
            safety_level="safe",
            input_schema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "default": "default_user"},
                },
            },
            handler=handle_automation_list_workflows,
        ),
        ToolMetadata(
            tool_id="automation_get_history",
            name="Get Workflow Execution History",
            description="Retrieves execution run history logs and analytics for workflows.",
            category=ToolCategory.AUTOMATION,
            capabilities=[ToolCapability.READ_ONLY.value],
            safety_level="safe",
            input_schema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string"},
                    "user_id": {"type": "string", "default": "default_user"},
                },
            },
            handler=handle_automation_get_history,
        ),
    ]
