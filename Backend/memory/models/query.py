from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from memory.models.memory import Memory, MemoryType


class MemoryQuery(BaseModel):
    query_text: str = ""
    types: Optional[List[MemoryType]] = None
    tags: Optional[List[str]] = None
    top_k: int = 5
    min_relevance: float = 0.5
    filter_params: Dict[str, Any] = Field(default_factory=dict)


class MemoryResult(BaseModel):
    memory: Memory
    score: float = 1.0
    matched_by: str = "direct"  # vector | keyword | graph | direct | hybrid


class MemorySummary(BaseModel):
    total_memories: int = 0
    count_by_type: Dict[str, int] = Field(default_factory=dict)
    total_nodes: int = 0
    total_edges: int = 0
    storage_bytes: int = 0
