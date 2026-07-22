from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel

class UIElementType(str, Enum):
    BUTTON = "button"
    INPUT = "input"
    PASSWORD = "password"
    DROPDOWN = "dropdown"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    LINK = "link"
    MENU = "menu"
    TOOLBAR = "toolbar"
    TAB = "tab"
    WINDOW = "window"
    DIALOG = "dialog"
    ICON = "icon"
    IMAGE = "image"
    SCROLLBAR = "scrollbar"
    STATUS_BAR = "status_bar"
    NAV_PANEL = "nav_panel"

class UIBoundingBox(BaseModel):
    x: int
    y: int
    width: int
    height: int
    center_x: int
    center_y: int

class UIElementNode(BaseModel):
    element_id: str
    element_type: UIElementType
    label: Optional[str] = None
    bbox: UIBoundingBox
    confidence: float
    is_clickable: bool = True
    is_enabled: bool = True
    is_visible: bool = True
    is_focused: bool = False
    parent_window: Optional[str] = None
    application: Optional[str] = None
    hierarchy_level: int = 1

class UIObservation(BaseModel):
    observation_id: str
    frame_id: Optional[str] = None
    timestamp: float
    active_window_title: Optional[str] = None
    active_process_name: Optional[str] = None
    ui_elements: List[UIElementNode]
    window_count: int = 1
    processing_time_seconds: float
