from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class Event(BaseModel):
    name: str
    data: Dict[str, Any]
    timestamp: float

class ActionStep(BaseModel):
    step_id: int
    tool_name: str
    arguments: Dict[str, Any]
    description: str

class ActionPlan(BaseModel):
    intent: str
    steps: List[ActionStep]
    execution_mode: str = "immediate"  # "immediate" | "background"
    requires_permission: bool = False

class TaskMetadata(BaseModel):
    task_id: str
    description: str
    status: str = "pending"  # "pending" | "running" | "completed" | "failed" | "cancelled"
    progress: float = 0.0     # 0.0 to 100.0
    started_time: float
    finished_time: Optional[float] = None
    current_step: str = "Initialized"
    error: Optional[str] = None

class StructuredExecutionLog(BaseModel):
    intent: str
    generated_plan: List[Dict[str, Any]]
    selected_tools: List[str]
    permissions: List[str]
    execution_time_seconds: float
    dry_run: bool
    success: bool
    results: List[Any]
    error: Optional[str] = None

class PermissionLevel:
    SAFE = "safe"
    ASK_ONCE = "ask_once"
    ALWAYS_CONFIRM = "always_confirm"
