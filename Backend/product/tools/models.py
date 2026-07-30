"""
Product 1.5 Tool Execution Engine Domain Models, Data Classes, and Enums.
"""
from enum import Enum
from typing import List, Dict, Any, Optional
import time
import uuid
from pydantic import BaseModel, Field


class ExecutionMode(str, Enum):
    SYNC = "sync"
    ASYNC = "async"
    STREAMING = "streaming"
    BACKGROUND = "background"
    SCHEDULED = "scheduled"


class ToolCapability(str, Enum):
    FILESYSTEM_READ = "filesystem:read"
    FILESYSTEM_WRITE = "filesystem:write"
    NETWORK_OUTBOUND = "network:outbound"
    SYSTEM_EXECUTE = "system:execute"
    DESKTOP_CONTROL = "desktop:control"
    BROWSER_AUTOMATION = "browser:automation"
    READ_ONLY = "read_only"


class ToolCategory(str, Enum):
    UTILITY = "utility"
    SYSTEM = "system"
    INFORMATION = "information"
    COMMUNICATION = "communication"
    AUTOMATION = "automation"
    PLUGIN = "plugin"


class RetryPolicyType(str, Enum):
    NEVER = "never"
    FIXED = "fixed"
    EXPONENTIAL_BACKOFF = "exponential_backoff"


class ExecutionStatusCode(str, Enum):
    SUCCESS = "SUCCESS"
    INVALID_INPUT = "INVALID_INPUT"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    TIMEOUT = "TIMEOUT"
    TOOL_ERROR = "TOOL_ERROR"
    INVALID_OUTPUT = "INVALID_OUTPUT"
    CANCELLED = "CANCELLED"


class RetryPolicy(BaseModel):
    policy_type: RetryPolicyType = RetryPolicyType.NEVER
    max_retries: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 10.0
    backoff_factor: float = 2.0
    retryable_exceptions: List[str] = Field(default_factory=lambda: ["TimeoutError", "ConnectionError", "RuntimeError"])


class ToolMetadata(BaseModel):
    tool_id: str
    name: str
    description: str
    version: str = "1.0.0"
    category: ToolCategory = ToolCategory.UTILITY
    capabilities: List[str] = Field(default_factory=list)
    safety_level: str = "safe"  # safe, confirmation_required, restricted
    supported_platforms: List[str] = Field(default_factory=lambda: ["windows", "macos", "linux"])
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: float = 10.0
    supports_async: bool = True
    supports_streaming: bool = False
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    owner: str = "core"  # core or plugin_id
    source: str = "built_in"  # built_in or plugin
    handler: Any = Field(default=None, exclude=True)

    class Config:
        arbitrary_types_allowed = True


class ExecutionContext(BaseModel):
    correlation_id: str = Field(default_factory=lambda: f"exec_{uuid.uuid4().hex[:12]}")
    tool_id: str
    user_id: str = "default_user"
    session_id: Optional[str] = None
    security_context: Optional[Any] = Field(default=None, exclude=True)
    user_preferences: Optional[Any] = Field(default=None, exclude=True)
    memory_provider: Optional[Any] = Field(default=None, exclude=True)
    plugin_reference: Optional[Any] = Field(default=None, exclude=True)
    request_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)

    class Config:
        arbitrary_types_allowed = True


class ToolExecutionResult(BaseModel):
    execution_id: str = Field(default_factory=lambda: f"res_{uuid.uuid4().hex[:12]}")
    correlation_id: str
    tool_id: str
    status: ExecutionStatusCode = ExecutionStatusCode.SUCCESS
    success: bool = True
    result_payload: Any = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: float = 0.0
    attempts: int = 1
    timestamp: float = Field(default_factory=time.time)


class ExecutionMetrics(BaseModel):
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_timeouts: int = 0
    total_retries: int = 0
    total_duration_ms: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p90_ms: float = 0.0
    latency_p99_ms: float = 0.0
    tool_usage_counts: Dict[str, int] = Field(default_factory=dict)
