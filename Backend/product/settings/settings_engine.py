"""
Public API Entrypoint for Phase P1.3 (Settings & Configuration).
Coordinates Settings Validation, Configuration Profile Inheritance, Change History, Backups, and EventBus Broadcasting.
"""
import uuid
import time
import logging
from typing import Optional, Dict, Any, List, Tuple

from .settings_models import (
    SettingDefinition,
    SettingValue,
    SettingProfile,
    SettingHistory,
    SettingBackup,
    ValidationResult,
    SettingCategory,
)
from .settings_store import SQLiteSettingsRepository
from .settings_validator import SettingsValidator
from .settings_profiles import SettingsProfileManager
from .settings_events import SettingsEventPublisher
from product.storage import SQLiteProductStorage
from brain.event_bus import event_bus, EventBus

logger = logging.getLogger("JARVIS_SettingsEngine")


class SettingsEngine:
    """
    Production-grade Settings & Configuration Public API Entrypoint for Phase P1.3.
    Integrates Metadata Registry, Dynamic Validation, Profile Inheritance, Change Tracking, and EventBus.
    """

    def __init__(
        self,
        repository: Optional[SQLiteSettingsRepository] = None,
        bus: Optional[EventBus] = None,
        product_storage: Optional[SQLiteProductStorage] = None,
    ):
        self.event_bus = bus or event_bus
        if repository:
            self.repository = repository
        else:
            p_storage = product_storage or SQLiteProductStorage()
            self.repository = SQLiteSettingsRepository(product_storage_instance=p_storage)

        self.validator = SettingsValidator()
        self.profile_manager = SettingsProfileManager(
            repository=self.repository,
            validator=self.validator,
        )
        self.event_publisher = SettingsEventPublisher(bus=self.event_bus)
        self._running: bool = False

    async def start(self) -> None:
        """Starts the Settings & Configuration engine service."""
        self._running = True
        logger.info("[SettingsEngine] Settings & Configuration service started successfully.")

    async def stop(self) -> None:
        """Stops the Settings & Configuration engine service cleanly."""
        self._running = False
        logger.info("[SettingsEngine] Settings & Configuration service stopped cleanly.")

    def get_setting(self, user_id: str, key: str, profile_id: Optional[str] = None) -> Any:
        """
        Retrieves setting value following inheritance resolution chain:
        Target Profile Override -> Parent Profile Override -> Default Profile Override -> System Registry Default.
        """
        return self.profile_manager.resolve_inherited_setting(user_id, key, profile_id)

    def set_setting(
        self, user_id: str, key: str, value: Any, profile_id: Optional[str] = None
    ) -> Tuple[Optional[SettingValue], ValidationResult]:
        """
        Validates, persists, records history, and emits SettingChanged event.
        """
        validation = self.validator.validate_setting(key, value)
        if not validation.valid:
            logger.warning(f"[SettingsEngine] Validation failed for setting '{key}': {validation.error_message}")
            return None, validation

        active_prof = self.profile_manager.get_active_profile(user_id)
        target_prof_id = profile_id or active_prof.profile_id
        defn = self.validator.get_definition(key)
        category = defn.category if defn else SettingCategory.ASSISTANT

        # Get old value for history tracking
        try:
            old_val = self.get_setting(user_id, key, target_prof_id)
        except Exception:
            old_val = None

        now = time.time()
        setting_val = SettingValue(
            setting_id=f"set_{str(uuid.uuid4())}",
            user_id=user_id,
            profile_id=target_prof_id,
            category=category,
            key=key,
            value=validation.sanitized_value,
            is_override=True,
            created_at=now,
            updated_at=now,
        )

        saved = self.repository.save_setting_value(setting_val)

        # Record history entry
        history_entry = SettingHistory(
            history_id=f"hist_{str(uuid.uuid4())}",
            user_id=user_id,
            setting_key=key,
            old_value=old_val,
            new_value=validation.sanitized_value,
            profile_id=target_prof_id,
            changed_at=now,
        )
        self.repository.record_history(history_entry)

        # Emit event
        self.event_publisher.emit_setting_changed(
            user_id=user_id,
            key=key,
            value=validation.sanitized_value,
            profile_id=target_prof_id,
            requires_restart=validation.requires_restart,
        )

        return saved, validation

    def reset_setting(self, user_id: str, key: str, profile_id: Optional[str] = None) -> bool:
        """Removes profile override for key, restoring inherited default, and emits SettingReset event."""
        active_prof = self.profile_manager.get_active_profile(user_id)
        target_prof_id = profile_id or active_prof.profile_id

        success = self.repository.delete_setting_value(user_id, key, target_prof_id)
        if success:
            self.event_publisher.emit_setting_reset(user_id, key, target_prof_id)
        return success

    def reset_category(self, user_id: str, category: SettingCategory, profile_id: Optional[str] = None) -> int:
        """Resets all overrides in a specific category for profile."""
        active_prof = self.profile_manager.get_active_profile(user_id)
        target_prof_id = profile_id or active_prof.profile_id

        overrides = self.repository.list_setting_values(user_id, target_prof_id, category=category)
        reset_count = 0
        for sv in overrides:
            if self.repository.delete_setting_value(user_id, sv.key, target_prof_id):
                reset_count += 1
                self.event_publisher.emit_setting_reset(user_id, sv.key, target_prof_id)

        return reset_count

    def reset_all(self, user_id: str, profile_id: Optional[str] = None) -> int:
        """Resets all setting overrides for profile."""
        active_prof = self.profile_manager.get_active_profile(user_id)
        target_prof_id = profile_id or active_prof.profile_id

        overrides = self.repository.list_setting_values(user_id, target_prof_id)
        reset_count = 0
        for sv in overrides:
            if self.repository.delete_setting_value(user_id, sv.key, target_prof_id):
                reset_count += 1
                self.event_publisher.emit_setting_reset(user_id, sv.key, target_prof_id)

        return reset_count

    def list_settings(
        self, user_id: str, category: Optional[SettingCategory] = None, profile_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Lists all resolved settings for category/profile."""
        definitions = self.validator.list_definitions(category=category)
        resolved: Dict[str, Any] = {}
        for defn in definitions:
            resolved[defn.key] = self.get_setting(user_id, defn.key, profile_id)
        return resolved

    def search_settings(
        self, user_id: str, query: str, category: Optional[SettingCategory] = None
    ) -> List[Dict[str, Any]]:
        """Searches setting definitions and matches resolved values."""
        query_terms = [t.strip().lower() for t in query.split()] if query else []
        definitions = self.validator.list_definitions(category=category)

        matches = []
        for defn in definitions:
            target_text = f"{defn.key.lower()} {defn.description.lower()}"
            if query_terms and all(term in target_text for term in query_terms):
                val = self.get_setting(user_id, defn.key)
                item = defn.to_dict()
                item["resolved_value"] = val
                matches.append(item)

        return matches

    def create_profile(
        self, user_id: str, name: str, description: str = "", parent_profile_id: Optional[str] = None
    ) -> SettingProfile:
        """Creates a new configuration profile and emits ProfileCreated event."""
        prof = self.profile_manager.create_profile(user_id, name, description, parent_profile_id)
        self.event_publisher.emit_profile_created(user_id, prof.profile_id, prof.name)
        return prof

    def duplicate_profile(self, user_id: str, profile_id: str, new_name: str) -> SettingProfile:
        """Duplicates a profile along with overrides."""
        dup = self.profile_manager.duplicate_profile(user_id, profile_id, new_name)
        self.event_publisher.emit_profile_created(user_id, dup.profile_id, dup.name)
        return dup

    def switch_profile(self, user_id: str, profile_id: str) -> SettingProfile:
        """
        Switches active profile and emits ProfileSwitched and ProfileActivated events.
        ProfileActivated notifies all subsystems to refresh cached settings cleanly.
        """
        prof = self.profile_manager.switch_profile(user_id, profile_id)
        overrides = self.repository.list_setting_values(user_id, prof.profile_id)

        self.event_publisher.emit_profile_switched(user_id, prof.profile_id, prof.name)
        self.event_publisher.emit_profile_activated(
            user_id=user_id,
            profile_id=prof.profile_id,
            name=prof.name,
            overrides_count=len(overrides),
        )
        return prof

    def delete_profile(self, user_id: str, profile_id: str) -> bool:
        """Deletes a profile by ID."""
        success = self.profile_manager.delete_profile(user_id, profile_id)
        if success:
            self.event_publisher.emit_profile_deleted(user_id, profile_id)
        return success

    def list_profiles(self, user_id: str) -> List[SettingProfile]:
        """Lists all configuration profiles for user ID."""
        self.profile_manager.ensure_default_profile(user_id)
        return self.repository.list_profiles(user_id)

    def export_settings(self, user_id: str, profile_id: Optional[str] = None) -> Dict[str, Any]:
        """Exports user profiles, active profile ID, and setting overrides to structured JSON payload."""
        active_prof = self.profile_manager.get_active_profile(user_id)
        target_prof_id = profile_id or active_prof.profile_id
        profiles = self.repository.list_profiles(user_id)
        overrides = self.repository.list_setting_values(user_id, target_prof_id)

        payload = {
            "version": "1.0",
            "exported_at": time.time(),
            "user_id": user_id,
            "active_profile_id": target_prof_id,
            "profiles": [p.to_dict() for p in profiles],
            "overrides": [sv.to_dict() for sv in overrides],
        }

        self.event_publisher.emit_settings_exported(user_id, target_prof_id)
        return payload

    def import_settings(self, user_id: str, settings_data: Dict[str, Any], profile_id: Optional[str] = None) -> Tuple[int, str]:
        """Imports setting overrides from JSON dictionary payload."""
        if not settings_data or "overrides" not in settings_data:
            return 0, "Invalid import payload."

        active_prof = self.profile_manager.get_active_profile(user_id)
        target_prof_id = profile_id or active_prof.profile_id

        imported_count = 0
        raw_overrides = settings_data.get("overrides", [])

        for item in raw_overrides:
            key = item.get("key")
            val = item.get("value")
            if key:
                saved_val, val_res = self.set_setting(user_id, key, val, target_prof_id)
                if saved_val:
                    imported_count += 1

        self.event_publisher.emit_settings_imported(user_id, imported_count)
        return imported_count, f"Successfully imported {imported_count} settings overrides."

    def backup_settings(self, user_id: str, name: str = "Automatic Backup") -> SettingBackup:
        """Creates a snapshot backup of user settings and profiles."""
        payload = self.export_settings(user_id)
        backup_id = f"bak_{str(uuid.uuid4())}"
        backup = SettingBackup(
            backup_id=backup_id,
            user_id=user_id,
            name=name,
            payload=payload,
            created_at=time.time(),
        )

        saved_backup = self.repository.create_backup(backup)
        self.event_publisher.emit_settings_backed_up(user_id, backup_id, name)
        return saved_backup

    def restore_settings(self, user_id: str, backup_id: str) -> bool:
        """Restores user settings from a snapshot backup."""
        backup = self.repository.get_backup(user_id, backup_id)
        if not backup or not backup.payload:
            return False

        imported_count, _ = self.import_settings(user_id, backup.payload)
        self.event_publisher.emit_settings_restored(user_id, backup_id)
        return True

    def validate_setting(self, key: str, value: Any) -> ValidationResult:
        """Validates a proposed setting value against registry constraints."""
        return self.validator.validate_setting(key, value)

    def get_metrics(self) -> Dict[str, Any]:
        """Returns operational metrics summary."""
        return {
            "status": "online" if self._running else "stopped",
            "phase": "P1.3",
            "subsystem": "ProductLayer.Settings",
        }

    def get_health(self) -> Dict[str, Any]:
        """Returns subsystem health status."""
        return {
            "healthy": self._running,
            "subsystem": "ProductLayer.Settings",
            "phase": "P1.3",
        }


# Global singleton instance
settings_engine = SettingsEngine()
