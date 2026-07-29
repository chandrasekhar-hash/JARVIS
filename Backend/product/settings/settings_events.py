"""
Settings Event Publisher for Phase P1.3 (Settings & Configuration).
Emits reactive events on EventBus for setting updates, profile activations, resets, backups, and restores.
"""
import logging
from typing import Optional, Dict, Any

from brain.event_bus import event_bus, EventBus

logger = logging.getLogger("JARVIS_SettingsEventPublisher")


class SettingsEventPublisher:
    """
    Event Publisher helper class emitting standardized settings platform events.
    """

    def __init__(self, bus: Optional[EventBus] = None):
        self.event_bus = bus or event_bus

    def emit_setting_changed(self, user_id: str, key: str, value: Any, profile_id: str, requires_restart: bool = False) -> None:
        self.event_bus.emit(
            "SettingChanged",
            user_id=user_id,
            key=key,
            value=value,
            profile_id=profile_id,
            requires_restart=requires_restart,
        )

    def emit_setting_reset(self, user_id: str, key: str, profile_id: str) -> None:
        self.event_bus.emit(
            "SettingReset",
            user_id=user_id,
            key=key,
            profile_id=profile_id,
        )

    def emit_profile_created(self, user_id: str, profile_id: str, name: str) -> None:
        self.event_bus.emit(
            "ProfileCreated",
            user_id=user_id,
            profile_id=profile_id,
            name=name,
        )

    def emit_profile_deleted(self, user_id: str, profile_id: str) -> None:
        self.event_bus.emit(
            "ProfileDeleted",
            user_id=user_id,
            profile_id=profile_id,
        )

    def emit_profile_switched(self, user_id: str, profile_id: str, name: str) -> None:
        self.event_bus.emit(
            "ProfileSwitched",
            user_id=user_id,
            profile_id=profile_id,
            name=name,
        )

    def emit_profile_activated(self, user_id: str, profile_id: str, name: str, overrides_count: int) -> None:
        """
        Emits high-level ProfileActivated event notifying all subsystems
        (Voice, Memory, Conversation Engine, Diagnostics) to refresh cached settings.
        """
        self.event_bus.emit(
            "ProfileActivated",
            user_id=user_id,
            profile_id=profile_id,
            name=name,
            overrides_count=overrides_count,
        )

    def emit_settings_imported(self, user_id: str, imported_count: int) -> None:
        self.event_bus.emit(
            "SettingsImported",
            user_id=user_id,
            imported_count=imported_count,
        )

    def emit_settings_exported(self, user_id: str, profile_id: str) -> None:
        self.event_bus.emit(
            "SettingsExported",
            user_id=user_id,
            profile_id=profile_id,
        )

    def emit_settings_backed_up(self, user_id: str, backup_id: str, name: str) -> None:
        self.event_bus.emit(
            "SettingsBackedUp",
            user_id=user_id,
            backup_id=backup_id,
            name=name,
        )

    def emit_settings_restored(self, user_id: str, backup_id: str) -> None:
        self.event_bus.emit(
            "SettingsRestored",
            user_id=user_id,
            backup_id=backup_id,
        )
