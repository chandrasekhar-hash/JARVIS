"""
JARVIS Product 1.7 - Automation Engine Domain Models.

Defines core data classes, enums, and configurations for Workflows, Triggers, Conditions, Actions, Runs, and Statuses.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
import uuid


class WorkflowStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    DISABLED = "DISABLED"
    ARCHIVED = "ARCHIVED"


class TriggerType(str, Enum):
    TIME_CRON = "TIME_CRON"
    TIME_INTERVAL = "TIME_INTERVAL"
    MANUAL = "MANUAL"
    FILESYSTEM = "FILESYSTEM"
    KNOWLEDGE_EVENT = "KNOWLEDGE_EVENT"
    PLUGIN_EVENT = "PLUGIN_EVENT"
    TOOL_EVENT = "TOOL_EVENT"


class ExecutionStrategy(str, Enum):
    SEQUENTIAL = "SEQUENTIAL"
    PARALLEL = "PARALLEL"


class RunStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class TriggerConfig:
    trigger_type: TriggerType
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    watch_directory: Optional[str] = None
    event_topic: Optional[str] = None
    custom_params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trigger_type": self.trigger_type.value,
            "cron_expression": self.cron_expression,
            "interval_seconds": self.interval_seconds,
            "watch_directory": self.watch_directory,
            "event_topic": self.event_topic,
            "custom_params": self.custom_params,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TriggerConfig":
        if not data:
            return cls(trigger_type=TriggerType.MANUAL)
        return cls(
            trigger_type=TriggerType(data.get("trigger_type", TriggerType.MANUAL.value)),
            cron_expression=data.get("cron_expression"),
            interval_seconds=data.get("interval_seconds"),
            watch_directory=data.get("watch_directory"),
            event_topic=data.get("event_topic"),
            custom_params=data.get("custom_params", {}),
        )


@dataclass
class ConditionConfig:
    condition_type: str
    target: str
    expected_value: Any = True
    operator: str = "equals"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition_type": self.condition_type,
            "target": self.target,
            "expected_value": self.expected_value,
            "operator": self.operator,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConditionConfig":
        return cls(
            condition_type=data.get("condition_type", "file_exists"),
            target=data.get("target", ""),
            expected_value=data.get("expected_value", True),
            operator=data.get("operator", "equals"),
        )


@dataclass
class ActionStep:
    step_id: str
    tool_id: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    continue_on_failure: bool = False
    timeout_seconds: float = 30.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "tool_id": self.tool_id,
            "arguments": self.arguments,
            "continue_on_failure": self.continue_on_failure,
            "timeout_seconds": self.timeout_seconds,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionStep":
        return cls(
            step_id=data.get("step_id", f"step_{uuid.uuid4().hex[:6]}"),
            tool_id=data.get("tool_id", ""),
            arguments=data.get("arguments", {}),
            continue_on_failure=data.get("continue_on_failure", False),
            timeout_seconds=float(data.get("timeout_seconds", 30.0)),
        )


@dataclass
class WorkflowPermissions:
    owner_id: str
    allowed_roles: List[str] = field(default_factory=lambda: ["admin", "user"])
    allowed_plugins: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "owner_id": self.owner_id,
            "allowed_roles": self.allowed_roles,
            "allowed_plugins": self.allowed_plugins,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowPermissions":
        if not data:
            return cls(owner_id="system")
        return cls(
            owner_id=data.get("owner_id", "system"),
            allowed_roles=data.get("allowed_roles", ["admin", "user"]),
            allowed_plugins=data.get("allowed_plugins", []),
        )


@dataclass
class RetryPolicyConfig:
    max_retries: int = 3
    initial_delay_seconds: float = 2.0
    backoff_factor: float = 2.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_retries": self.max_retries,
            "initial_delay_seconds": self.initial_delay_seconds,
            "backoff_factor": self.backoff_factor,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RetryPolicyConfig":
        if not data:
            return cls()
        return cls(
            max_retries=data.get("max_retries", 3),
            initial_delay_seconds=float(data.get("initial_delay_seconds", 2.0)),
            backoff_factor=float(data.get("backoff_factor", 2.0)),
        )


@dataclass
class Workflow:
    workflow_id: str
    name: str
    description: str
    owner: str
    version: int = 1
    trigger: TriggerConfig = field(default_factory=lambda: TriggerConfig(trigger_type=TriggerType.MANUAL))
    conditions: List[ConditionConfig] = field(default_factory=list)
    actions: List[ActionStep] = field(default_factory=list)
    execution_strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL
    permissions: WorkflowPermissions = field(default_factory=lambda: WorkflowPermissions(owner_id="system"))
    timeout_seconds: float = 300.0
    retry_policy: RetryPolicyConfig = field(default_factory=RetryPolicyConfig)
    status: WorkflowStatus = WorkflowStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    tags: List[str] = field(default_factory=list)

    @classmethod
    def create_new(
        cls,
        name: str,
        description: str,
        owner: str,
        trigger: TriggerConfig,
        actions: List[ActionStep],
        conditions: Optional[List[ConditionConfig]] = None,
        execution_strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL,
        permissions: Optional[WorkflowPermissions] = None,
        timeout_seconds: float = 300.0,
        retry_policy: Optional[RetryPolicyConfig] = None,
        tags: Optional[List[str]] = None,
    ) -> "Workflow":
        wf_id = f"wf_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow()
        return cls(
            workflow_id=wf_id,
            name=name,
            description=description,
            owner=owner,
            version=1,
            trigger=trigger,
            conditions=conditions or [],
            actions=actions,
            execution_strategy=execution_strategy,
            permissions=permissions or WorkflowPermissions(owner_id=owner),
            timeout_seconds=timeout_seconds,
            retry_policy=retry_policy or RetryPolicyConfig(),
            status=WorkflowStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            tags=tags or [],
        )


@dataclass
class WorkflowRunRecord:
    run_id: str
    workflow_id: str
    workflow_name: str
    owner: str
    trigger_type: TriggerType
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    status: RunStatus = RunStatus.QUEUED
    steps_completed: int = 0
    total_steps: int = 0
    error_details: Optional[str] = None
    step_logs_json: str = "[]"

    @classmethod
    def create_new(
        cls,
        workflow_id: str,
        workflow_name: str,
        owner: str,
        trigger_type: TriggerType,
        total_steps: int,
    ) -> "WorkflowRunRecord":
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        return cls(
            run_id=run_id,
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            owner=owner,
            trigger_type=trigger_type,
            start_time=datetime.utcnow(),
            status=RunStatus.QUEUED,
            total_steps=total_steps,
        )
