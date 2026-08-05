from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    EXPIRED = "EXPIRED"
    TERMINATED = "TERMINATED"

class CameraFrame(BaseModel):
    frame_index: int
    timestamp: float
    data: bytes = Field(exclude=True)
    width: int = 1280
    height: int = 720
    hash_code: str = ""

class SceneChangeResult(BaseModel):
    should_analyze: bool
    score: float
    reason: str

class FocusTarget(BaseModel):
    object_name: str
    description: Optional[str] = None
    updated_at: float

class VisionSessionState(BaseModel):
    session_id: str
    status: SessionStatus
    active_focus: Optional[str] = None
    keyframe_count: int = 0
    scene_summary: Optional[str] = None
    last_accessed_at: float

class CameraAnalysisResult(BaseModel):
    session_id: str
    text: str
    scene_changed: bool
    active_focus: Optional[str] = None
    task_type: str = "CAMERA_VISION"
    visual_summary: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

