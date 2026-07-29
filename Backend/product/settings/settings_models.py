"""
Data Models, Enums, and Setting Definitions for Phase P1.3 (Settings & Configuration).
Provides central metadata registry definitions, setting values, profile inheritance entities, and validation models.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List, Union
import time


class SettingCategory(str, Enum):
    """Setting category classification."""
    ASSISTANT = "ASSISTANT"
    MEMORY = "MEMORY"
    VOICE = "VOICE"
    APPEARANCE = "APPEARANCE"
    NOTIFICATIONS = "NOTIFICATIONS"
    PRIVACY = "PRIVACY"
    PERFORMANCE = "PERFORMANCE"
    DEVELOPER = "DEVELOPER"


class SettingDataType(str, Enum):
    """Primitive or complex data type for setting values."""
    STRING = "STRING"
    INT = "INT"
    FLOAT = "FLOAT"
    BOOL = "BOOL"
    JSON = "JSON"
    ENUM = "ENUM"


class ThemeOption(str, Enum):
    """Appearance theme options."""
    DARK = "DARK"
    LIGHT = "LIGHT"
    GLASSMORPHISM = "GLASSMORPHISM"
    HIGH_CONTRAST = "HIGH_CONTRAST"
    SYSTEM = "SYSTEM"


@dataclass
class SettingDefinition:
    """Registry metadata definition for a single configurable setting."""
    key: str
    category: SettingCategory
    data_type: SettingDataType
    default_value: Any
    description: str = ""
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    allowed_values: Optional[List[Any]] = None
    requires_restart: bool = False
    is_experimental: bool = False
    is_read_only: bool = False
    is_secret: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serializes definition to dictionary format."""
        return {
            "key": self.key,
            "category": self.category.value if isinstance(self.category, SettingCategory) else str(self.category),
            "data_type": self.data_type.value if isinstance(self.data_type, SettingDataType) else str(self.data_type),
            "default_value": self.default_value,
            "description": self.description,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "allowed_values": self.allowed_values,
            "requires_restart": self.requires_restart,
            "is_experimental": self.is_experimental,
            "is_read_only": self.is_read_only,
            "is_secret": self.is_secret,
        }


@dataclass
class SettingValue:
    """Persisted value override for a specific user and profile."""
    setting_id: str
    user_id: str
    profile_id: str
    category: SettingCategory
    key: str
    value: Any
    is_override: bool = True
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "setting_id": self.setting_id,
            "user_id": self.user_id,
            "profile_id": self.profile_id,
            "category": self.category.value if isinstance(self.category, SettingCategory) else str(self.category),
            "key": self.key,
            "value": self.value,
            "is_override": self.is_override,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
        }


@dataclass
class SettingProfile:
    """Configuration profile entity supporting parent profile inheritance."""
    profile_id: str
    user_id: str
    name: str
    parent_profile_id: Optional[str] = None
    description: str = ""
    is_active: bool = False
    is_default: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "user_id": self.user_id,
            "parent_profile_id": self.parent_profile_id,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class SettingHistory:
    """Audit log record for setting modifications."""
    history_id: str
    user_id: str
    setting_key: str
    old_value: Any
    new_value: Any
    profile_id: str
    changed_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "history_id": self.history_id,
            "user_id": self.user_id,
            "setting_key": self.setting_key,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "profile_id": self.profile_id,
            "changed_at": self.changed_at,
        }


@dataclass
class SettingBackup:
    """Snapshot backup entity for user settings."""
    backup_id: str
    user_id: str
    name: str
    payload: Dict[str, Any]
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "backup_id": self.backup_id,
            "user_id": self.user_id,
            "name": self.name,
            "payload": self.payload,
            "created_at": self.created_at,
        }


@dataclass
class ValidationResult:
    """Outcome of setting validation check."""
    valid: bool
    error_message: str = ""
    requires_restart: bool = False
    sanitized_value: Optional[Any] = None
