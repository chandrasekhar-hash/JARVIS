import time
import uuid
from enum import Enum, IntEnum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


class ContextSource(str, Enum):
    MEMORY = "memory"
    USER_MODEL = "user_model"
    CONVERSATION = "conversation"
    GOAL_MANAGER = "goal_manager"
    DESKTOP = "desktop"
    RUNTIME = "runtime"
    ENVIRONMENT = "environment"


class ContextPriority(IntEnum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    BACKGROUND = 5


class ContextProviderInfo(BaseModel):
    model_config = ConfigDict(frozen=False)

    provider_id: str = Field(min_length=1)
    source: ContextSource
    name: str = Field(min_length=1)
    priority: ContextPriority = ContextPriority.MEDIUM
    is_healthy: bool = True
    capabilities: List[str] = Field(default_factory=list)
    quota_weight: float = Field(default=1.0, ge=0.0, le=10.0)


class ContextChunk(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: str = Field(default_factory=lambda: f"chunk_{uuid.uuid4().hex[:12]}")
    source: ContextSource
    provider_id: str = Field(min_length=1)
    content: str = Field(min_length=1)
    priority: ContextPriority = ContextPriority.MEDIUM
    estimated_tokens: int = Field(default=0, ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class TokenAllocation(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider_id: str = Field(min_length=1)
    allocated_tokens: int = Field(ge=0)
    used_tokens: int = Field(ge=0)
    was_trimmed: bool = False


class ProviderStatistics(BaseModel):
    model_config = ConfigDict(frozen=False)

    provider_id: str = Field(min_length=1)
    total_calls: int = Field(default=0, ge=0)
    successful_calls: int = Field(default=0, ge=0)
    failed_calls: int = Field(default=0, ge=0)
    average_latency_ms: float = Field(default=0.0, ge=0.0)


class ContextAssemblyMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    assembly_id: str = Field(default_factory=lambda: f"asm_{uuid.uuid4().hex[:12]}")
    total_chunks_collected: int = Field(default=0, ge=0)
    chunks_after_dedup: int = Field(default=0, ge=0)
    chunks_after_trim: int = Field(default=0, ge=0)
    total_tokens_budgeted: int = Field(default=0, ge=0)
    total_tokens_used: int = Field(default=0, ge=0)
    assembly_time_ms: float = Field(default=0.0, ge=0.0)
    timestamp: float = Field(default_factory=time.time)


class CognitiveContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    context_id: str = Field(default_factory=lambda: f"ctx_{uuid.uuid4().hex[:12]}")
    user_id: str = Field(default="default_user", min_length=1)
    chunks: List[ContextChunk] = Field(default_factory=list)
    formatted_prompt_context: str = Field(default="")
    token_count: int = Field(default=0, ge=0)
    sources_included: List[ContextSource] = Field(default_factory=list)
    assembly_metrics: ContextAssemblyMetrics = Field(default_factory=ContextAssemblyMetrics)
    timestamp: float = Field(default_factory=time.time)
