import os
import sqlite3
import json
import time
from typing import List, Optional, Dict, Any
from identity.identity_models import (
    UserProfile,
    DeviceProfile,
    DeviceTrustState,
    SessionToken,
    SessionStatus,
    SecurityStatus
)
from tools.telemetry import log_structured, backend_log

SCHEMA_VERSION = "v1_identity_security"

class SQLiteIdentityStorage:
    """
    SQLite persistence layer for identity, device trust, session tokens, and security settings
    reusing the primary database at logs/jarvis_memory.db.
    Includes schema_version table and migration tracking.
    """

    def __init__(self, db_path: str = "logs/jarvis_memory.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Schema version table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version TEXT PRIMARY KEY,
                    applied_at REAL NOT NULL,
                    description TEXT
                )
            """)

            # Check and apply schema version
            cursor.execute("SELECT version FROM schema_version WHERE version = ?", (SCHEMA_VERSION,))
            row = cursor.fetchone()
            if not row:
                cursor.execute(
                    "INSERT INTO schema_version (version, applied_at, description) VALUES (?, ?, ?)",
                    (SCHEMA_VERSION, time.time(), "Phase 8.1 Identity and Security Layer schema")
                )

            # 2. User Profiles table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    email TEXT,
                    avatar_url TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    locale TEXT NOT NULL,
                    timezone TEXT NOT NULL,
                    theme TEXT NOT NULL,
                    ai_defaults_json TEXT NOT NULL
                )
            """)

            # 3. Device Profiles table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS device_profiles (
                    device_id TEXT PRIMARY KEY,
                    device_name TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    architecture TEXT NOT NULL,
                    os_version TEXT NOT NULL,
                    app_version TEXT NOT NULL,
                    installation_date REAL NOT NULL,
                    public_key TEXT NOT NULL,
                    public_key_fingerprint TEXT NOT NULL,
                    trust_state TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)

            # 4. Session Tokens table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_tokens (
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

            # 5. Security Settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS security_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)

            conn.commit()
            log_structured(backend_log, "INFO", f"[IdentityStorage] Initialized Identity & Security tables in '{self.db_path}' ({SCHEMA_VERSION})")

    # --- User Profile CRUD ---

    def save_user_profile(self, profile: UserProfile) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO user_profiles (user_id, display_name, email, avatar_url, created_at, updated_at, locale, timezone, theme, ai_defaults_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    display_name=excluded.display_name,
                    email=excluded.email,
                    avatar_url=excluded.avatar_url,
                    updated_at=excluded.updated_at,
                    locale=excluded.locale,
                    timezone=excluded.timezone,
                    theme=excluded.theme,
                    ai_defaults_json=excluded.ai_defaults_json
                """,
                (
                    profile.user_id,
                    profile.display_name,
                    profile.email,
                    profile.avatar_url,
                    profile.created_at,
                    profile.updated_at,
                    profile.locale,
                    profile.timezone,
                    profile.theme,
                    json.dumps(profile.ai_defaults)
                )
            )
            conn.commit()

    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return UserProfile(
                user_id=row["user_id"],
                display_name=row["display_name"],
                email=row["email"],
                avatar_url=row["avatar_url"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                locale=row["locale"],
                timezone=row["timezone"],
                theme=row["theme"],
                ai_defaults=json.loads(row["ai_defaults_json"])
            )

    def get_primary_user_profile(self) -> Optional[UserProfile]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM user_profiles ORDER BY created_at ASC LIMIT 1")
            row = cursor.fetchone()
            if not row:
                return None
            return UserProfile(
                user_id=row["user_id"],
                display_name=row["display_name"],
                email=row["email"],
                avatar_url=row["avatar_url"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                locale=row["locale"],
                timezone=row["timezone"],
                theme=row["theme"],
                ai_defaults=json.loads(row["ai_defaults_json"])
            )

    # --- Device Profile CRUD ---

    def save_device_profile(self, device: DeviceProfile) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO device_profiles (device_id, device_name, platform, architecture, os_version, app_version, installation_date, public_key, public_key_fingerprint, trust_state, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(device_id) DO UPDATE SET
                    device_name=excluded.device_name,
                    platform=excluded.platform,
                    architecture=excluded.architecture,
                    os_version=excluded.os_version,
                    app_version=excluded.app_version,
                    public_key=excluded.public_key,
                    public_key_fingerprint=excluded.public_key_fingerprint,
                    trust_state=excluded.trust_state,
                    updated_at=excluded.updated_at
                """,
                (
                    device.device_id,
                    device.device_name,
                    device.platform,
                    device.architecture,
                    device.os_version,
                    device.app_version,
                    device.installation_date,
                    device.public_key,
                    device.public_key_fingerprint,
                    device.trust_state.value,
                    device.updated_at
                )
            )
            conn.commit()

    def get_device_profile(self, device_id: str) -> Optional[DeviceProfile]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM device_profiles WHERE device_id = ?", (device_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return DeviceProfile(
                device_id=row["device_id"],
                device_name=row["device_name"],
                platform=row["platform"],
                architecture=row["architecture"],
                os_version=row["os_version"],
                app_version=row["app_version"],
                installation_date=row["installation_date"],
                public_key=row["public_key"],
                public_key_fingerprint=row["public_key_fingerprint"],
                trust_state=DeviceTrustState(row["trust_state"]),
                updated_at=row["updated_at"]
            )

    def get_primary_device_profile(self) -> Optional[DeviceProfile]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM device_profiles ORDER BY installation_date ASC LIMIT 1")
            row = cursor.fetchone()
            if not row:
                return None
            return DeviceProfile(
                device_id=row["device_id"],
                device_name=row["device_name"],
                platform=row["platform"],
                architecture=row["architecture"],
                os_version=row["os_version"],
                app_version=row["app_version"],
                installation_date=row["installation_date"],
                public_key=row["public_key"],
                public_key_fingerprint=row["public_key_fingerprint"],
                trust_state=DeviceTrustState(row["trust_state"]),
                updated_at=row["updated_at"]
            )

    # --- Session Token CRUD ---

    def save_session_token(self, token: SessionToken) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO session_tokens (session_id, user_id, device_id, access_token, refresh_token, expires_at, refresh_expires_at, created_at, status, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    status=excluded.status,
                    expires_at=excluded.expires_at,
                    refresh_expires_at=excluded.refresh_expires_at
                """,
                (
                    token.session_id,
                    token.user_id,
                    token.device_id,
                    token.access_token,
                    token.refresh_token,
                    token.expires_at,
                    token.refresh_expires_at,
                    token.created_at,
                    token.status.value,
                    token.ip_address,
                    token.user_agent
                )
            )
            conn.commit()

    def get_session_by_access_token(self, access_token: str) -> Optional[SessionToken]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM session_tokens WHERE access_token = ?", (access_token,))
            row = cursor.fetchone()
            if not row:
                return None
            return SessionToken(
                session_id=row["session_id"],
                user_id=row["user_id"],
                device_id=row["device_id"],
                access_token=row["access_token"],
                refresh_token=row["refresh_token"],
                expires_at=row["expires_at"],
                refresh_expires_at=row["refresh_expires_at"],
                created_at=row["created_at"],
                status=SessionStatus(row["status"]),
                ip_address=row["ip_address"] or "127.0.0.1",
                user_agent=row["user_agent"] or "JARVIS Local Agent"
            )

    def get_session_by_refresh_token(self, refresh_token: str) -> Optional[SessionToken]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM session_tokens WHERE refresh_token = ?", (refresh_token,))
            row = cursor.fetchone()
            if not row:
                return None
            return SessionToken(
                session_id=row["session_id"],
                user_id=row["user_id"],
                device_id=row["device_id"],
                access_token=row["access_token"],
                refresh_token=row["refresh_token"],
                expires_at=row["expires_at"],
                refresh_expires_at=row["refresh_expires_at"],
                created_at=row["created_at"],
                status=SessionStatus(row["status"]),
                ip_address=row["ip_address"] or "127.0.0.1",
                user_agent=row["user_agent"] or "JARVIS Local Agent"
            )

    def list_active_sessions(self, user_id: str) -> List[SessionToken]:
        with self._get_connection() as conn:
            now = time.time()
            cursor = conn.execute(
                "SELECT * FROM session_tokens WHERE user_id = ? AND status = ? AND expires_at > ?",
                (user_id, SessionStatus.ACTIVE.value, now)
            )
            rows = cursor.fetchall()
            return [
                SessionToken(
                    session_id=r["session_id"],
                    user_id=r["user_id"],
                    device_id=r["device_id"],
                    access_token=r["access_token"],
                    refresh_token=r["refresh_token"],
                    expires_at=r["expires_at"],
                    refresh_expires_at=r["refresh_expires_at"],
                    created_at=r["created_at"],
                    status=SessionStatus(r["status"]),
                    ip_address=r["ip_address"] or "127.0.0.1",
                    user_agent=r["user_agent"] or "JARVIS Local Agent"
                )
                for r in rows
            ]

identity_storage = SQLiteIdentityStorage()
