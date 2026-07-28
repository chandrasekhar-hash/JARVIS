import os
import sqlite3
import json
import time
from typing import Dict, Any, Optional
from config.settings import cloud_settings

CLOUD_SCHEMA_VERSION = "v1_cloud_backend"

class CloudDatabaseManager:
    """
    Cloud Database Manager managing connections and migrations for PostgreSQL / SQLite.
    Initializes cloud tables from CLOUD_ARCHITECTURE.md specification.
    """

    def __init__(self, db_url: str = None):
        self.db_url = db_url or cloud_settings.database_url
        if self.db_url.startswith("sqlite:///"):
            self.sqlite_path = self.db_url.replace("sqlite:///", "")
            os.makedirs(os.path.dirname(self.sqlite_path), exist_ok=True)
        else:
            self.sqlite_path = "logs/jarvis_cloud_dev.db"
            os.makedirs("logs", exist_ok=True)

        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Cloud Schema Version Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cloud_schema_version (
                    version TEXT PRIMARY KEY,
                    applied_at REAL NOT NULL,
                    description TEXT
                )
            """)

            cursor.execute("SELECT version FROM cloud_schema_version WHERE version = ?", (CLOUD_SCHEMA_VERSION,))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO cloud_schema_version (version, applied_at, description) VALUES (?, ?, ?)",
                    (CLOUD_SCHEMA_VERSION, time.time(), "Phase 8.2 Cloud Backend Infrastructure schema")
                )

            # 2. Cloud Users Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cloud_users (
                    user_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    email TEXT,
                    avatar_url TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    preferences_json TEXT NOT NULL
                )
            """)

            # 3. Cloud Devices Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cloud_devices (
                    device_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    device_name TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    architecture TEXT NOT NULL,
                    os_version TEXT NOT NULL,
                    app_version TEXT NOT NULL,
                    public_key TEXT NOT NULL,
                    public_key_fingerprint TEXT NOT NULL,
                    trust_state TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES cloud_users(user_id)
                )
            """)

            # 4. Cloud Sessions Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cloud_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    access_token TEXT NOT NULL,
                    refresh_token TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    refresh_expires_at REAL NOT NULL,
                    created_at REAL NOT NULL,
                    status TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT
                )
            """)

            # 5. Cloud Audit Logs Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cloud_audit_logs (
                    log_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    user_id TEXT,
                    device_id TEXT,
                    action TEXT NOT NULL,
                    status TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
            """)

            # 6. Cloud Configurations Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cloud_configurations (
                    config_key TEXT PRIMARY KEY,
                    config_value TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)

            conn.commit()

db_manager = CloudDatabaseManager()
