from enum import Enum
from typing import List, Dict, Any, Optional
import time
from pydantic import BaseModel, Field


class JobType(str, Enum):
    ONE_TIME = "one_time"
    INTERVAL = "interval"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class JobStatus(str, Enum):
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    MISSED = "missed"


class ScheduleTrigger(BaseModel):
    job_type: JobType = JobType.INTERVAL
    expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    time_of_day: Optional[str] = "08:00"  # HH:MM format
    day_of_week: Optional[int] = None  # 0=Monday, 6=Sunday
    day_of_month: Optional[int] = None  # 1-31
    run_at: Optional[float] = None  # Timestamp for one_time jobs


class ScheduledJob(BaseModel):
    job_id: str
    task_name: str
    description: str
    trigger: ScheduleTrigger
    enabled: bool = True
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    last_run: Optional[float] = None
    next_run: float = 0.0
    status: JobStatus = JobStatus.SCHEDULED
    execution_count: int = 0
    failure_count: int = 0
    max_retries: int = 3
    retry_backoff_factor: float = 2.0
    timeout_seconds: int = 300
    params: Dict[str, Any] = Field(default_factory=dict)
    # Extensible future-proofing fields (Phase 8 Cloud / Phase 9 Plugins)
    node_id: str = "local_node"
    remote_origin: Optional[str] = None
    plugin_id: Optional[str] = None


class JobExecutionRecord(BaseModel):
    execution_id: str
    job_id: str
    task_name: str
    start_time: float
    end_time: Optional[float] = None
    duration_seconds: Optional[float] = None
    status: JobStatus
    error_message: Optional[str] = None
    retry_attempt: int = 0
    result_summary: Optional[str] = None


class SchedulerMetrics(BaseModel):
    total_jobs: int = 0
    enabled_jobs: int = 0
    running_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    missed_jobs: int = 0
    total_executions: int = 0
    average_duration_seconds: float = 0.0
    scheduler_uptime_seconds: float = 0.0
    is_running: bool = False


class TaskDefinition(BaseModel):
    name: str
    description: str
    category: str = "general"
    default_schedule: Optional[str] = "Every day at 08:00"
    enabled: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
