from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel

class ApplicationCategory(str, Enum):
    CODING = "coding"
    BROWSING = "browsing"
    DOCUMENTATION = "documentation"
    FILE_MANAGEMENT = "file_management"
    TERMINAL = "terminal"
    SETTINGS = "settings"
    MEDIA = "media"
    SYSTEM_DIALOG = "system_dialog"
    GENERAL = "general"

class VisualChangeType(str, Enum):
    WINDOW_OPENED = "window_opened"
    WINDOW_CLOSED = "window_closed"
    WINDOW_MOVED = "window_moved"
    WINDOW_RESIZED = "window_resized"
    APP_SWITCHED = "app_switched"
    TEXT_CHANGED = "text_changed"
    DIALOG_APPEARED = "dialog_appeared"
    NOTIFICATION_APPEARED = "notification_appeared"
    LOADING_COMPLETED = "loading_completed"
    SCREEN_UNCHANGED = "screen_unchanged"

class ApplicationContext(BaseModel):
    app_name: str
    window_title: str
    category: ApplicationCategory
    is_focused: bool = True

class VisualChange(BaseModel):
    change_id: str
    timestamp: float
    change_type: VisualChangeType
    description: str
    confidence: float = 1.0

class SceneSummary(BaseModel):
    headline: str
    detected_workflow: str
    active_app: ApplicationContext
    open_windows_count: int
    has_dialogs: bool = False
    has_errors: bool = False

class SceneObservation(BaseModel):
    observation_id: str
    frame_id: Optional[str] = None
    timestamp: float
    summary: SceneSummary
    all_windows: List[ApplicationContext]
    recent_changes: List[VisualChange]
