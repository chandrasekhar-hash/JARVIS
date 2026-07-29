"""
J.A.R.V.I.S. Product Layer Phase P1.3 (Settings & Configuration) Package Initialization.
Exports settings models, registry metadata definitions, interfaces, store repositories, profile inheritance manager, and public settings engine.
"""
from .settings_models import (
    SettingCategory,
    SettingDataType,
    ThemeOption,
    SettingDefinition,
    SettingValue,
    SettingProfile,
    SettingHistory,
    SettingBackup,
    ValidationResult,
)
from .settings_interfaces import (
    ISettingsRepository,
    ISettingsValidator,
    ISettingsProfileManager,
)
from .settings_migration import SettingsSchemaMigration
from .settings_store import SQLiteSettingsRepository
from .settings_validator import SETTINGS_REGISTRY, SettingsValidator
from .settings_profiles import SettingsProfileManager
from .settings_events import SettingsEventPublisher
from .settings_engine import SettingsEngine, settings_engine

__all__ = [
    "SettingCategory",
    "SettingDataType",
    "ThemeOption",
    "SettingDefinition",
    "SettingValue",
    "SettingProfile",
    "SettingHistory",
    "SettingBackup",
    "ValidationResult",
    "ISettingsRepository",
    "ISettingsValidator",
    "ISettingsProfileManager",
    "SettingsSchemaMigration",
    "SQLiteSettingsRepository",
    "SETTINGS_REGISTRY",
    "SettingsValidator",
    "SettingsProfileManager",
    "SettingsEventPublisher",
    "SettingsEngine",
    "settings_engine",
]
