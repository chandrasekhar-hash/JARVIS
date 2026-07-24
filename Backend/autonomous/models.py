import time
import uuid
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class GoalStatus(str, Enum):
    CREATED = "created"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class Task(BaseModel):
    task_id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:8]}")
    goal_id: str
    name: str
    description: str
    dependencies: List[str] = Field(default_factory=list)
    suggested_tool: Optional[str] = None
    input_params: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: float = 30.0
    max_retries: int = 3
    weight: float = 1.0


class Goal(BaseModel):
    goal_id: str = Field(default_factory=lambda: f"goal_{uuid.uuid4().hex[:8]}")
    user_intent: str
    status: GoalStatus = GoalStatus.CREATED
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    summary_result: Optional[str] = None


class ExecutionPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:8]}")
    goal_id: str
    tasks: Dict[str, Task] = Field(default_factory=dict)
    dag_edges: Dict[str, List[str]] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)


class TaskResult(BaseModel):
    task_id: str
    status: ExecutionState
    output: Optional[Any] = None
    error: Optional[str] = None
    execution_time_seconds: float = 0.0
    timestamp: float = Field(default_factory=time.time)


class RecoveryAttempt(BaseModel):
    attempt_id: str = Field(default_factory=lambda: f"rec_{uuid.uuid4().hex[:8]}")
    task_id: str
    strategy: str  # "retry" | "tool_switch" | "replan" | "escalate"
    success: bool
    details: str
    timestamp: float = Field(default_factory=time.time)


class ProgressSnapshot(BaseModel):
    goal_id: str
    overall_progress_pct: float = 0.0
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    in_progress_tasks: int = 0
    current_state: GoalStatus = GoalStatus.CREATED
    estimated_remaining_seconds: Optional[float] = None
    updated_at: float = Field(default_factory=time.time)


class WorkflowCheckpoint(BaseModel):
    checkpoint_id: str = Field(default_factory=lambda: f"chk_{uuid.uuid4().hex[:8]}")
    workflow_id: str
    goal_id: str
    plan: ExecutionPlan
    task_states: Dict[str, ExecutionState] = Field(default_factory=dict)
    task_results: Dict[str, TaskResult] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)
