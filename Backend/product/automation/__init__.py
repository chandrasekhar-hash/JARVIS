"""
J.A.R.V.I.S. Product 1.7 - Automation Engine Package Initialization.
Exports Automation Manager, Workflow Manager, Models, Interfaces, Scheduler, Triggers, Conditions, Queue, History, and Tools.
"""

from .models import (
    Workflow,
    WorkflowStatus,
    TriggerType,
    ExecutionStrategy,
    RunStatus,
    TriggerConfig,
    ConditionConfig,
    ActionStep,
    WorkflowPermissions,
    RetryPolicyConfig,
    WorkflowRunRecord,
)
from .interfaces import (
    IWorkflowValidator,
    IConditionEvaluator,
    IActionExecutor,
    ITriggerListener,
    IScheduler,
    ITaskQueue,
    IExecutionHistoryStore,
    INotificationChannel,
)
from .workflow_manager import WorkflowManager
from .validator import WorkflowValidator
from .registry import WorkflowRegistry
from .storage import SQLiteExecutionHistoryStore
from .triggers import (
    BaseTriggerListener,
    TimeTrigger,
    EventWatcher,
    FilesystemWatcher,
    ManualTrigger,
)
from .conditions import ConditionEvaluator
from .queue import TaskQueue
from .recovery import RetryManager, TimeoutManager
from .executor import ActionExecutor
from .notifications import (
    NotificationInterface,
    DesktopNotifier,
    VoiceNotifier,
    WebUINotifier,
    notification_interface,
)
from .telemetry import AutomationTelemetry, automation_telemetry
from .logging import AutomationLogger, automation_logger
from .scheduler import AutomationScheduler
from .automation_engine import AutomationManager, automation_manager_instance
from .tools import (
    handle_automation_create_workflow,
    handle_automation_trigger_workflow,
    handle_automation_pause_workflow,
    handle_automation_resume_workflow,
    handle_automation_delete_workflow,
    handle_automation_list_workflows,
    handle_automation_get_history,
    get_automation_tool_metadatas,
)

__all__ = [
    "Workflow",
    "WorkflowStatus",
    "TriggerType",
    "ExecutionStrategy",
    "RunStatus",
    "TriggerConfig",
    "ConditionConfig",
    "ActionStep",
    "WorkflowPermissions",
    "RetryPolicyConfig",
    "WorkflowRunRecord",
    "IWorkflowValidator",
    "IConditionEvaluator",
    "IActionExecutor",
    "ITriggerListener",
    "IScheduler",
    "ITaskQueue",
    "IExecutionHistoryStore",
    "INotificationChannel",
    "WorkflowManager",
    "WorkflowValidator",
    "WorkflowRegistry",
    "SQLiteExecutionHistoryStore",
    "BaseTriggerListener",
    "TimeTrigger",
    "EventWatcher",
    "FilesystemWatcher",
    "ManualTrigger",
    "ConditionEvaluator",
    "TaskQueue",
    "RetryManager",
    "TimeoutManager",
    "ActionExecutor",
    "NotificationInterface",
    "DesktopNotifier",
    "VoiceNotifier",
    "WebUINotifier",
    "notification_interface",
    "AutomationTelemetry",
    "automation_telemetry",
    "AutomationLogger",
    "automation_logger",
    "AutomationScheduler",
    "AutomationManager",
    "automation_manager_instance",
    "handle_automation_create_workflow",
    "handle_automation_trigger_workflow",
    "handle_automation_pause_workflow",
    "handle_automation_resume_workflow",
    "handle_automation_delete_workflow",
    "handle_automation_list_workflows",
    "handle_automation_get_history",
    "get_automation_tool_metadatas",
]
