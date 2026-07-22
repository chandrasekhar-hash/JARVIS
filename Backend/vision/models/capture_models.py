from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel

class CaptureMode(str, Enum):
    SNAPSHOT = "snapshot"
    CONTINUOUS = "continuous"
    FOCUSED_WINDOW = "focused_window"
    REGION = "region"

class VisionState(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"

class CapturePermissionState(str, Enum):
    DENIED = "denied"
    ALLOW_ONCE = "allow_once"
    ALWAYS_ALLOW = "always_allow"

class DisplayInfo(BaseModel):
    index: int
    is_primary: bool
    x: int
    y: int
    width: int
    height: int
    name: str

class BoundingBox(BaseModel):
    x: int
    y: int
    width: int
    height: int

class CaptureTarget(BaseModel):
    mode: CaptureMode = CaptureMode.SNAPSHOT
    monitor_index: int = 0
    region: Optional[BoundingBox] = None
    target_window_title: Optional[str] = None

class CaptureFrame(BaseModel):
    frame_id: str
    timestamp: float
    monitor_index: int
    resolution: Dict[str, int]  # {"width": int, "height": int}
    format: str = "RGB"
    base64_data: Optional[str] = None
    byte_size: int = 0
    has_changed: bool = True
