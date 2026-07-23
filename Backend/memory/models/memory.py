import time
import uuid
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    PREFERENCE = "preference"
    PROJECT = "project"


class RetentionPolicy(str, Enum):
    PERMANENT = "permanent"       # Never auto-decay (e.g. core preferences)
    EPISODIC = "episodic"         # Standard decay window (e.g. 30-day default)
    TRANSIENT = "transient"       # Rapid decay window (e.g. 24-hour default)
    PINNED = "pinned"             # User-pinned (exempt from purging/archival)


class MemoryMetadata(BaseModel):
    importance_score: float = Field(default=5.0, ge=1.0, le=10.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    last_accessed: float = Field(default_factory=time.time)
    access_count: int = Field(default=0)
    expires_at: Optional[float] = None
    pinned: bool = Field(default=False)
    source: str = "conversation"   # conversation | vision | task | user_input
    retention_policy: RetentionPolicy = RetentionPolicy.EPISODIC
    tags: List[str] = Field(default_factory=list)
    privacy_level: str = "normal"  # normal | sensitive | private


class MemoryChunk(BaseModel):
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    memory_id: str
    content: str
    embedding: Optional[List[float]] = None
    chunk_index: int = 0


class MemoryRelationship(BaseModel):
    relationship_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str
    target_id: str
    relation_type: str  # e.g., "REFERENCES", "EXTENDS", "SUPERSEDES"
    weight: float = 1.0


class Memory(BaseModel):
    memory_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: MemoryType
    title: str
    content: str
    summary: str = ""
    chunks: List[MemoryChunk] = Field(default_factory=list)
    metadata: MemoryMetadata = Field(default_factory=MemoryMetadata)
