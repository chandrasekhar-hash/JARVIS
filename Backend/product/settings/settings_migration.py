"""
Database Schema Migration Manager for Phase P1.3 (Settings & Configuration).
Upgrades SQLite database schema from Version 2 to Version 3 using schema_metadata version tracking.
"""
import time
import logging

logger = logging.getLogger("JARVIS_SettingsSchemaMigration")


class SettingsSchemaMigration:
    """
    Handles seamless migration of the J.A.R.V.I.S. Product database schema to Version 3.
    """

    TARGET_VERSION = 3

    @classmethod
    def migrate(cls, storage_instance) -> bool:
        """
        Executes schema migration to version 3 if current schema_version is less than 3.
        """
        current_version = storage_instance.get_schema_version()
        if current_version >= cls.TARGET_VERSION:
            logger.info(f"[SettingsSchemaMigration] Schema already up-to-date (Version {current_version}).")
            return True

        logger.info(f"[SettingsSchemaMigration] Upgrading database schema from Version {current_version} to {cls.TARGET_VERSION}...")
        now = time.time()

        with storage_instance._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS setting_profiles (
                    profile_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    parent_profile_id TEXT,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    is_active INTEGER DEFAULT 0,
                    is_default INTEGER DEFAULT 0,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS settings (
                    setting_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    profile_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    is_override INTEGER DEFAULT 1,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    version INTEGER DEFAULT 1,
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY(profile_id) REFERENCES setting_profiles(profile_id) ON DELETE CASCADE,
                    UNIQUE(user_id, profile_id, key)
                );

                CREATE TABLE IF NOT EXISTS setting_history (
                    history_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    setting_key TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    profile_id TEXT NOT NULL,
                    changed_at REAL NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS setting_backups (
                    backup_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_settings_user_profile ON settings(user_id, profile_id);
                CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key);
                CREATE INDEX IF NOT EXISTS idx_profiles_user ON setting_profiles(user_id);
            """)

            # Update schema_metadata
            conn.execute(
                "UPDATE schema_metadata SET schema_version = ?, updated_at = ?",
                (cls.TARGET_VERSION, now),
            )

        logger.info(f"[SettingsSchemaMigration] Successfully upgraded database schema to Version {cls.TARGET_VERSION}.")
        return True
