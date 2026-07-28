from enum import Enum
from typing import List, Dict, Any, Optional
import time
from pydantic import BaseModel, Field


class PluginStatus(str, Enum):
    DISCOVERED = "discovered"
    VALIDATED = "validated"
    LOADED = "loaded"
    RUNNING = "running"
    DISABLED = "disabled"
    FAILED = "failed"
    UNLOADED = "unloaded"


class PluginPermissionEnum(str, Enum):
    FILESYSTEM = "filesystem"
    BROWSER = "browser"
    DESKTOP = "desktop"
    NETWORK = "network"
    SHELL = "shell"
    CAMERA = "camera"
    MICROPHONE = "microphone"
    CLIPBOARD = "clipboard"


class PluginManifest(BaseModel):
    id: str
    name: str
    version: str = "1.0.0"
    author: str = "Anonymous"
    description: str
    permissions: List[str] = Field(default_factory=list)
    entry: str = "main.py"
    minimum_version: str = "1.0.0"
    category: str = "utility"
    enabled: bool = True
    dependencies: List[str] = Field(default_factory=list)


class PluginState(BaseModel):
    plugin_id: str
    manifest: PluginManifest
    status: PluginStatus = PluginStatus.DISCOVERED
    plugin_dir: str
    loaded_at: Optional[float] = None
    error_message: Optional[str] = None
    health_ok: bool = True
    registered_tools: List[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True
