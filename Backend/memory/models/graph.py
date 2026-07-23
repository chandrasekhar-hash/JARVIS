import time
import uuid
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class KnowledgeNode(BaseModel):
    node_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str
    type: str  # Person | Application | File | Project | Topic | ActionSequence
    properties: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)


class KnowledgeEdge(BaseModel):
    edge_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_node_id: str
    target_node_id: str
    relationship: str  # USES | CREATED | OPENED | PART_OF | PREFERS | RELATED_TO | FOLLOWS
    weight: float = 1.0
    confidence: float = 1.0
    created_at: float = Field(default_factory=time.time)

