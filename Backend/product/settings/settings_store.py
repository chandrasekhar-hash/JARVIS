"""
SQLite Settings Repository Engine for Phase P1.3 (Settings & Configuration).
Implements thread-safe SQLite persistence for settings overrides, configuration profiles, change history, and backups.
Enforces 100% user data isolation across all database operations.
"""
import json
import sqlite3
import time
import logging
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from .settings_models import (
    SettingValue,
    SettingProfile,
    SettingHistory,
    SettingBackup,
    SettingCategory,
)
from .settings_interfaces import ISettingsRepository
from .settings_migration import SettingsSchemaMigration

logger = logging.getLogger("JARVIS_SQLiteSettingsRepository")


class SQLiteSettingsRepository(ISettingsRepository):
    """
    SQLite persistence implementation for all Phase P1.3 Settings models.
    Guarantees user-level security isolation and profile inheritance storage.
    """

    def __init__(self, product_storage_instance):
        self.storage = product_storage_instance
        # Ensure database schema is migrated to Version 3
        SettingsSchemaMigration.migrate(self.storage)

    @contextmanager
    def _get_connection(self):
        """Reuses connection manager from ProductStorage."""
        with self.storage._get_connection() as conn:
            yield conn

    # -------------------------------------------------------------------------
    # Settings Values CRUD
    # -------------------------------------------------------------------------
    def save_setting_value(self, setting_value: SettingValue) -> SettingValue:
        setting_value.updated_at = time.time()
        val_str = json.dumps(setting_value.value)

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO settings (
                    setting_id, user_id, profile_id, category, key, value,
                    is_override, created_at, updated_at, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, profile_id, key) DO UPDATE SET
                    value = excluded.value,
                    is_override = excluded.is_override,
                    updated_at = excluded.updated_at,
                    version = settings.version + 1
                """,
                (
                    setting_value.setting_id,
                    setting_value.user_id,
                    setting_value.profile_id,
                    setting_value.category.value if isinstance(setting_value.category, SettingCategory) else str(setting_value.category),
                    setting_value.key,
                    val_str,
                    1 if setting_value.is_override else 0,
                    setting_value.created_at,
                    setting_value.updated_at,
                    setting_value.version,
                ),
            )

        return setting_value

    def get_setting_value(self, user_id: str, key: str, profile_id: str) -> Optional[SettingValue]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM settings WHERE user_id = ? AND key = ? AND profile_id = ?",
                (user_id, key, profile_id),
            ).fetchone()
            if row:
                return self._row_to_setting_value(row)
        return None

    def delete_setting_value(self, user_id: str, key: str, profile_id: str) -> bool:
        with self._get_connection() as conn:
            res = conn.execute(
                "DELETE FROM settings WHERE user_id = ? AND key = ? AND profile_id = ?",
                (user_id, key, profile_id),
            )
            return res.rowcount > 0

    def list_setting_values(
        self, user_id: str, profile_id: str, category: Optional[SettingCategory] = None
    ) -> List[SettingValue]:
        sql = "SELECT * FROM settings WHERE user_id = ? AND profile_id = ?"
        params: List[Any] = [user_id, profile_id]

        if category:
            sql += " AND category = ?"
            params.append(category.value if isinstance(category, SettingCategory) else str(category))

        with self._get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_setting_value(r) for r in rows]

    def _row_to_setting_value(self, row: sqlite3.Row) -> SettingValue:
        raw_val = json.loads(row["value"])
        return SettingValue(
            setting_id=row["setting_id"],
            user_id=row["user_id"],
            profile_id=row["profile_id"],
            category=SettingCategory(row["category"]),
            key=row["key"],
            value=raw_val,
            is_override=bool(row["is_override"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            version=row["version"],
        )

    # -------------------------------------------------------------------------
    # Configuration Profiles CRUD
    # -------------------------------------------------------------------------
    def create_profile(self, profile: SettingProfile) -> SettingProfile:
        with self._get_connection() as conn:
            if profile.is_active:
                conn.execute("UPDATE setting_profiles SET is_active = 0 WHERE user_id = ?", (profile.user_id,))

            conn.execute(
                """
                INSERT INTO setting_profiles (
                    profile_id, user_id, parent_profile_id, name, description,
                    is_active, is_default, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile.profile_id,
                    profile.user_id,
                    profile.parent_profile_id,
                    profile.name,
                    profile.description,
                    1 if profile.is_active else 0,
                    1 if profile.is_default else 0,
                    profile.created_at,
                    profile.updated_at,
                ),
            )
        return profile

    def get_profile(self, user_id: str, profile_id: str) -> Optional[SettingProfile]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM setting_profiles WHERE user_id = ? AND profile_id = ?",
                (user_id, profile_id),
            ).fetchone()
            if row:
                return self._row_to_profile(row)
        return None

    def get_active_profile(self, user_id: str) -> Optional[SettingProfile]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM setting_profiles WHERE user_id = ? AND is_active = 1",
                (user_id,),
            ).fetchone()
            if row:
                return self._row_to_profile(row)
        return None

    def update_profile(self, profile: SettingProfile) -> SettingProfile:
        profile.updated_at = time.time()
        with self._get_connection() as conn:
            if profile.is_active:
                conn.execute("UPDATE setting_profiles SET is_active = 0 WHERE user_id = ?", (profile.user_id,))

            conn.execute(
                """
                UPDATE setting_profiles
                SET parent_profile_id = ?, name = ?, description = ?,
                    is_active = ?, is_default = ?, updated_at = ?
                WHERE user_id = ? AND profile_id = ?
                """,
                (
                    profile.parent_profile_id,
                    profile.name,
                    profile.description,
                    1 if profile.is_active else 0,
                    1 if profile.is_default else 0,
                    profile.updated_at,
                    profile.user_id,
                    profile.profile_id,
                ),
            )
        return profile

    def delete_profile(self, user_id: str, profile_id: str) -> bool:
        with self._get_connection() as conn:
            res = conn.execute(
                "DELETE FROM setting_profiles WHERE user_id = ? AND profile_id = ? AND is_default = 0",
                (user_id, profile_id),
            )
            return res.rowcount > 0

    def list_profiles(self, user_id: str) -> List[SettingProfile]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM setting_profiles WHERE user_id = ? ORDER BY is_default DESC, name ASC",
                (user_id,),
            ).fetchall()
            return [self._row_to_profile(r) for r in rows]

    def _row_to_profile(self, row: sqlite3.Row) -> SettingProfile:
        return SettingProfile(
            profile_id=row["profile_id"],
            user_id=row["user_id"],
            parent_profile_id=row["parent_profile_id"],
            name=row["name"],
            description=row["description"],
            is_active=bool(row["is_active"]),
            is_default=bool(row["is_default"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    # -------------------------------------------------------------------------
    # History & Backups
    # -------------------------------------------------------------------------
    def record_history(self, history_entry: SettingHistory) -> SettingHistory:
        old_str = json.dumps(history_entry.old_value)
        new_str = json.dumps(history_entry.new_value)

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO setting_history (
                    history_id, user_id, setting_key, old_value, new_value, profile_id, changed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    history_entry.history_id,
                    history_entry.user_id,
                    history_entry.setting_key,
                    old_str,
                    new_str,
                    history_entry.profile_id,
                    history_entry.changed_at,
                ),
            )
        return history_entry

    def list_history(self, user_id: str, setting_key: Optional[str] = None) -> List[SettingHistory]:
        sql = "SELECT * FROM setting_history WHERE user_id = ?"
        params: List[Any] = [user_id]
        if setting_key:
            sql += " AND setting_key = ?"
            params.append(setting_key)

        sql += " ORDER BY changed_at DESC LIMIT 100"

        with self._get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [
                SettingHistory(
                    history_id=r["history_id"],
                    user_id=r["user_id"],
                    setting_key=r["setting_key"],
                    old_value=json.loads(r["old_value"]) if r["old_value"] else None,
                    new_value=json.loads(r["new_value"]) if r["new_value"] else None,
                    profile_id=r["profile_id"],
                    changed_at=r["changed_at"],
                )
                for r in rows
            ]

    def create_backup(self, backup: SettingBackup) -> SettingBackup:
        payload_str = json.dumps(backup.payload)
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO setting_backups (backup_id, user_id, name, payload, created_at) VALUES (?, ?, ?, ?, ?)",
                (backup.backup_id, backup.user_id, backup.name, payload_str, backup.created_at),
            )
        return backup

    def get_backup(self, user_id: str, backup_id: str) -> Optional[SettingBackup]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM setting_backups WHERE user_id = ? AND backup_id = ?",
                (user_id, backup_id),
            ).fetchone()
            if row:
                return SettingBackup(
                    backup_id=row["backup_id"],
                    user_id=row["user_id"],
                    name=row["name"],
                    payload=json.loads(row["payload"]),
                    created_at=row["created_at"],
                )
        return None

    def list_backups(self, user_id: str) -> List[SettingBackup]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM setting_backups WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
            return [
                SettingBackup(
                    backup_id=r["backup_id"],
                    user_id=r["user_id"],
                    name=r["name"],
                    payload=json.loads(r["payload"]),
                    created_at=r["created_at"],
                )
                for r in rows
            ]
