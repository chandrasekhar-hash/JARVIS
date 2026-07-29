"""
Abstract Interfaces for Phase P1.3 (Settings & Configuration).
Adheres strictly to SOLID principles and Dependency Injection standards.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Tuple
from .settings_models import (
    SettingDefinition,
    SettingValue,
    SettingProfile,
    SettingHistory,
    SettingBackup,
    ValidationResult,
    SettingCategory,
)


class ISettingsRepository(ABC):
    """Abstract Repository Interface for Settings persistence and profile storage."""

    @abstractmethod
    def save_setting_value(self, setting_value: SettingValue) -> SettingValue:
        """Persists or updates a SettingValue record."""
        pass

    @abstractmethod
    def get_setting_value(self, user_id: str, key: str, profile_id: str) -> Optional[SettingValue]:
        """Retrieves a specific SettingValue record by key and profile ID."""
        pass

    @abstractmethod
    def delete_setting_value(self, user_id: str, key: str, profile_id: str) -> bool:
        """Deletes a setting override for a given profile."""
        pass

    @abstractmethod
    def list_setting_values(
        self, user_id: str, profile_id: str, category: Optional[SettingCategory] = None
    ) -> List[SettingValue]:
        """Lists persisted setting overrides for a user and profile."""
        pass

    @abstractmethod
    def create_profile(self, profile: SettingProfile) -> SettingProfile:
        """Creates a new configuration profile."""
        pass

    @abstractmethod
    def get_profile(self, user_id: str, profile_id: str) -> Optional[SettingProfile]:
        """Retrieves a configuration profile by ID."""
        pass

    @abstractmethod
    def get_active_profile(self, user_id: str) -> Optional[SettingProfile]:
        """Retrieves the active profile for a user ID."""
        pass

    @abstractmethod
    def update_profile(self, profile: SettingProfile) -> SettingProfile:
        """Updates a configuration profile."""
        pass

    @abstractmethod
    def delete_profile(self, user_id: str, profile_id: str) -> bool:
        """Deletes a configuration profile by ID."""
        pass

    @abstractmethod
    def list_profiles(self, user_id: str) -> List[SettingProfile]:
        """Lists all configuration profiles for a user ID."""
        pass

    @abstractmethod
    def record_history(self, history_entry: SettingHistory) -> SettingHistory:
        """Records an audit log entry for a setting change."""
        pass

    @abstractmethod
    def list_history(self, user_id: str, setting_key: Optional[str] = None) -> List[SettingHistory]:
        """Lists setting change history."""
        pass

    @abstractmethod
    def create_backup(self, backup: SettingBackup) -> SettingBackup:
        """Creates a snapshot backup of user settings."""
        pass

    @abstractmethod
    def get_backup(self, user_id: str, backup_id: str) -> Optional[SettingBackup]:
        """Retrieves a setting backup snapshot by ID."""
        pass

    @abstractmethod
    def list_backups(self, user_id: str) -> List[SettingBackup]:
        """Lists setting backup snapshots for a user ID."""
        pass


class ISettingsValidator(ABC):
    """Abstract Interface for validating setting values against central metadata registry."""

    @abstractmethod
    def validate_setting(self, key: str, value: Any) -> ValidationResult:
        """Validates a setting value against registered constraints."""
        pass

    @abstractmethod
    def get_definition(self, key: str) -> Optional[SettingDefinition]:
        """Retrieves setting definition by key."""
        pass

    @abstractmethod
    def list_definitions(self, category: Optional[SettingCategory] = None) -> List[SettingDefinition]:
        """Lists all registered setting definitions."""
        pass


class ISettingsProfileManager(ABC):
    """Abstract Interface for configuration profile management and inheritance resolution."""

    @abstractmethod
    def get_active_profile(self, user_id: str) -> SettingProfile:
        """Retrieves active profile for a user ID."""
        pass

    @abstractmethod
    def switch_profile(self, user_id: str, profile_id: str) -> SettingProfile:
        """Switches active profile for a user ID."""
        pass

    @abstractmethod
    def resolve_inherited_setting(self, user_id: str, key: str, profile_id: str) -> Any:
        """Resolves setting value following inheritance chain (Profile -> Parent Profile -> System Default)."""
        pass
