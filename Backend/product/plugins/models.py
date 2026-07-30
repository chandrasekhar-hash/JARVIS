"""
Product 1.4 Plugin & Skills Framework Domain Models and Enums.
"""
from enum import Enum
from typing import List, Dict, Any, Optional
import time
from pydantic import BaseModel, Field


class PluginStatus(str, Enum):
    DISCOVERED = "discovered"
    VALIDATED = "validated"
    RESOLVED = "resolved"
    REGISTERED = "registered"
    INITIALIZED = "initialized"
    ACTIVATED = "activated"
    EXECUTING = "executing"
    DEACTIVATED = "deactivated"
    DISABLED = "disabled"
    FAILED = "failed"
    UNLOADED = "unloaded"


class PluginPermissionScope(str, Enum):
    FILESYSTEM_READ = "filesystem.read"
    FILESYSTEM_WRITE = "filesystem.write"
    NETWORK_HTTP = "network.http"
    CLIPBOARD = "clipboard"
    NOTIFICATIONS = "notifications"
    SYSTEM_EXECUTE = "system.execute"
    CALENDAR_READ = "calendar.read"
    EMAIL_SEND = "email.send"


class PermissionConsentStatus(str, Enum):
    GRANTED = "granted"
    DENIED = "denied"
    PROMPT = "prompt"


class PluginCategory(str, Enum):
    UTILITY = "utility"
    PRODUCTIVITY = "productivity"
    INFORMATION = "information"
    AUTOMATION = "automation"
    DEVELOPER = "developer"
    MEDIA = "media"


class PluginManifest(BaseModel):
    id: str
    name: str
    version: str = "1.0.0"
    author: str = "Anonymous"
    description: str = ""
    entry_point: str = "main.py"
    permissions: List[str] = Field(default_factory=list)
    dependencies: Dict[str, str] = Field(default_factory=dict)
    minimum_jarvis_version: str = "1.0.0"
    configuration_schema: Dict[str, Any] = Field(default_factory=dict)
    enabled_by_default: bool = True
    category: str = PluginCategory.UTILITY.value


class PluginPermissionGrant(BaseModel):
    scope: str
    status: PermissionConsentStatus = PermissionConsentStatus.PROMPT
    granted_at: Optional[float] = None
    justification: Optional[str] = None


class SkillDefinition(BaseModel):
    skill_id: str
    plugin_id: str
    name: str
    description: str
    handler: Any = Field(default=None, exclude=True)
    intent_patterns: List[str] = Field(default_factory=list)
    parameters_schema: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class CommandDefinition(BaseModel):
    trigger_keyword: str
    plugin_id: str
    handler: Any = Field(default=None, exclude=True)
    description: str = ""

    class Config:
        arbitrary_types_allowed = True


class PluginState(BaseModel):
    plugin_id: str
    manifest: PluginManifest
    status: PluginStatus = PluginStatus.DISCOVERED
    plugin_dir: str
    loaded_at: Optional[float] = None
    error_message: Optional[str] = None
    health_ok: bool = True
    consecutive_failures: int = 0
    registered_skills: List[str] = Field(default_factory=list)
    registered_commands: List[str] = Field(default_factory=list)
    registered_events: List[str] = Field(default_factory=list)
    permission_grants: Dict[str, PluginPermissionGrant] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True
