import os
from pydantic import BaseModel

class AutonomousConfig(BaseModel):
    """Configuration settings for Phase 5 Autonomous Execution System."""
    DEFAULT_TASK_TIMEOUT_SECONDS: float = 30.0
    MAX_TASK_RETRIES: int = 3
    MAX_REPLAN_DEPTH: int = 3
    DEFAULT_WORKER_CONCURRENCY: int = 4
    ENABLE_VISUAL_VERIFICATION: bool = True
    ENABLE_MEMORY_ENHANCEMENT: bool = True

    # Checkpoint Persistence Version
    WORKFLOW_CHECKPOINT_VERSION: str = "5.0.0"

    # Event Names
    EVENT_GOAL_CREATED: str = "GoalCreated"
    EVENT_GOAL_STARTED: str = "GoalStarted"
    EVENT_GOAL_COMPLETED: str = "GoalCompleted"
    EVENT_GOAL_CANCELLED: str = "GoalCancelled"
    EVENT_GOAL_FAILED: str = "GoalFailed"
    EVENT_GOAL_PAUSED: str = "GoalPaused"
    EVENT_GOAL_RESUMED: str = "GoalResumed"
    EVENT_GOAL_PROGRESS_CHANGED: str = "GoalProgressChanged"
    EVENT_TASK_CREATED: str = "TaskCreated"
    EVENT_TASK_STARTED: str = "TaskStarted"
    EVENT_TASK_COMPLETED: str = "TaskCompleted"
    EVENT_TASK_FAILED: str = "TaskFailed"
    EVENT_PROGRESS_UPDATED: str = "ProgressUpdated"
    EVENT_EXECUTION_STARTED: str = "ExecutionStarted"
    EVENT_EXECUTION_COMPLETED: str = "ExecutionCompleted"
    EVENT_EXECUTION_CANCELLED: str = "ExecutionCancelled"
    EVENT_EXECUTION_PAUSED: str = "ExecutionPaused"
    EVENT_EXECUTION_RESUMED: str = "ExecutionResumed"
    EVENT_RECOVERY_STARTED: str = "RecoveryStarted"
    EVENT_RECOVERY_RETRY_SCHEDULED: str = "RecoveryRetryScheduled"
    EVENT_RECOVERY_ALTERNATIVE_TOOL: str = "RecoveryAlternativeTool"
    EVENT_RECOVERY_REPLANNED: str = "RecoveryReplanned"
    EVENT_RECOVERY_ESCALATED: str = "RecoveryEscalated"
    EVENT_RECOVERY_SUCCEEDED: str = "RecoverySucceeded"
    EVENT_RECOVERY_FAILED: str = "RecoveryFailed"
    EVENT_WORKFLOW_CREATED: str = "WorkflowCreated"
    EVENT_CHECKPOINT_SAVED: str = "CheckpointSaved"
    EVENT_CHECKPOINT_LOADED: str = "CheckpointLoaded"
    EVENT_WORKFLOW_RESUMED: str = "WorkflowResumed"
    EVENT_WORKFLOW_ARCHIVED: str = "WorkflowArchived"
    EVENT_WORKFLOW_DELETED: str = "WorkflowDeleted"
    EVENT_CHECKPOINT_VALIDATION_FAILED: str = "CheckpointValidationFailed"
    EVENT_WORKFLOW_CHECKPOINT_CREATED: str = "WorkflowCheckpointCreated"

autonomous_config = AutonomousConfig()
