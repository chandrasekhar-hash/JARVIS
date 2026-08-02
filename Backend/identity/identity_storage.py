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

            # 6. User Credentials table for authentication
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_credentials (
                    username TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    display_name TEXT,
                    created_at REAL NOT NULL,
                    password_updated_at REAL DEFAULT 0
                )
            """)

            # Ensure columns exist if tables were created in an earlier schema
            try:
                cursor.execute("ALTER TABLE user_credentials ADD COLUMN password_updated_at REAL DEFAULT 0")
            except Exception:
                pass

            try:
                cursor.execute("ALTER TABLE user_credentials ADD COLUMN is_verified INTEGER DEFAULT 0")
                cursor.execute("UPDATE user_credentials SET is_verified = 1 WHERE is_verified IS NULL OR is_verified = 0")
            except Exception:
                pass

            # 7. OTP Challenges table for password reset & registration
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS otp_challenges (
                    challenge_id TEXT PRIMARY KEY,
                    email TEXT NOT NULL,
                    otp_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    attempts INTEGER DEFAULT 0,
                    resend_count INTEGER DEFAULT 1,
                    last_sent_at REAL NOT NULL,
                    verified INTEGER DEFAULT 0,
                    purpose TEXT DEFAULT 'password_reset'
                )
            """)

            try:
                cursor.execute("ALTER TABLE otp_challenges ADD COLUMN purpose TEXT DEFAULT 'password_reset'")
            except Exception:
                pass

            # 8. Password Reset Tokens table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    reset_token TEXT PRIMARY KEY,
                    email TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    used INTEGER DEFAULT 0
                )
            """)

            # 9. Registration Verification Tokens table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS registration_verification_tokens (
                    verification_token TEXT PRIMARY KEY,
                    email TEXT NOT NULL,
                    username TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    used INTEGER DEFAULT 0
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

    # --- User Credentials CRUD ---

    def save_user_credential(self, username: str, email: str, password_hash: str, display_name: str = None, is_verified: int = 0) -> Dict[str, Any]:
        clean_username = username.strip().lower()
        clean_email = email.strip().lower()
        now = time.time()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO user_credentials (username, email, password_hash, display_name, created_at, is_verified)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    email=excluded.email,
                    password_hash=excluded.password_hash,
                    display_name=excluded.display_name,
                    is_verified=excluded.is_verified
                """,
                (clean_username, clean_email, password_hash, display_name or clean_username, now, is_verified)
            )
            conn.commit()
        return {
            "username": clean_username,
            "email": clean_email,
            "display_name": display_name or clean_username,
            "created_at": now,
            "is_verified": is_verified
        }

    def mark_user_verified(self, email_or_username: str) -> bool:
        clean_id = email_or_username.strip().lower()
        with self._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE user_credentials SET is_verified = 1 WHERE LOWER(email) = ? OR LOWER(username) = ?",
                (clean_id, clean_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_user_credential_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        clean_username = username.strip().lower()
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM user_credentials WHERE LOWER(username) = ?", (clean_username,))
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

    def get_user_credential_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        clean_email = email.strip().lower()
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM user_credentials WHERE LOWER(email) = ?", (clean_email,))
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

    def get_user_credential_by_identifier(self, identifier: str) -> Optional[Dict[str, Any]]:
        clean_id = identifier.strip().lower()
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM user_credentials WHERE LOWER(username) = ? OR LOWER(email) = ?",
                (clean_id, clean_id)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

    def update_user_password(self, email: str, new_password_hash: str) -> bool:
        clean_email = email.strip().lower()
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE user_credentials SET password_hash = ?, password_updated_at = ? WHERE LOWER(email) = ?",
                (new_password_hash, now, clean_email)
            )
            conn.commit()
            return cursor.rowcount > 0

    def update_user_profile_fields(self, username: str, display_name: str = None, new_username: str = None) -> Optional[Dict[str, Any]]:
        """Update display_name and/or username for a user. Returns updated record or None on failure."""
        clean_username = username.strip().lower()
        with self._get_connection() as conn:
            row_cursor = conn.execute(
                "SELECT * FROM user_credentials WHERE LOWER(username) = ?", (clean_username,)
            )
            row = row_cursor.fetchone()
            if not row:
                return None

            updated_display_name = display_name.strip() if display_name and display_name.strip() else row["display_name"]
            updated_username = new_username.strip().lower() if new_username and new_username.strip() else clean_username

            # If username is being changed, verify no conflict
            if updated_username != clean_username:
                conflict = conn.execute(
                    "SELECT username FROM user_credentials WHERE LOWER(username) = ? AND LOWER(username) != ?",
                    (updated_username, clean_username)
                ).fetchone()
                if conflict:
                    return {"error": "username_taken"}

            conn.execute(
                """UPDATE user_credentials
                   SET display_name = ?, username = ?
                   WHERE LOWER(username) = ?""",
                (updated_display_name, updated_username, clean_username)
            )
            conn.commit()

            updated_row = conn.execute(
                "SELECT * FROM user_credentials WHERE LOWER(username) = ?", (updated_username,)
            ).fetchone()
            if not updated_row:
                return None
            return dict(updated_row)

    def revoke_all_user_sessions(self, username_or_email: str) -> None:
        clean_id = username_or_email.strip().lower()
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE session_tokens SET status = 'revoked' WHERE user_id = ? OR user_id IN (SELECT username FROM user_credentials WHERE LOWER(email) = ?)",
                (clean_id, clean_id)
            )
            conn.commit()

    # --- OTP Challenges CRUD ---

    def create_otp_challenge(self, email: str, otp_hash: str, salt: str, purpose: str = "password_reset") -> Dict[str, Any]:
        clean_email = email.strip().lower()
        now = time.time()
        expires_at = now + 600  # 10 minutes
        challenge_id = f"otp_{os.urandom(8).hex()}"

        with self._get_connection() as conn:
            # Invalidate previous unverified challenges for this email and purpose
            conn.execute(
                "UPDATE otp_challenges SET verified = -1 WHERE LOWER(email) = ? AND purpose = ? AND verified = 0",
                (clean_email, purpose)
            )
            conn.execute(
                """
                INSERT INTO otp_challenges (challenge_id, email, otp_hash, salt, created_at, expires_at, attempts, resend_count, last_sent_at, verified, purpose)
                VALUES (?, ?, ?, ?, ?, ?, 0, 1, ?, 0, ?)
                """,
                (challenge_id, clean_email, otp_hash, salt, now, expires_at, now, purpose)
            )
            conn.commit()

        return {
            "challenge_id": challenge_id,
            "email": clean_email,
            "created_at": now,
            "expires_at": expires_at,
            "purpose": purpose
        }

    def get_latest_otp_challenge(self, email: str, purpose: str = "password_reset") -> Optional[Dict[str, Any]]:
        clean_email = email.strip().lower()
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM otp_challenges WHERE LOWER(email) = ? AND purpose = ? AND verified = 0 ORDER BY created_at DESC LIMIT 1",
                (clean_email, purpose)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

    def increment_otp_attempt(self, challenge_id: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE otp_challenges SET attempts = attempts + 1 WHERE challenge_id = ?",
                (challenge_id,)
            )
            cursor = conn.execute("SELECT attempts FROM otp_challenges WHERE challenge_id = ?", (challenge_id,))
            row = cursor.fetchone()
            attempts = row["attempts"] if row else 0
            if attempts >= 5:
                conn.execute("UPDATE otp_challenges SET verified = -1 WHERE challenge_id = ?", (challenge_id,))
            conn.commit()
            return attempts

    def mark_otp_challenge_verified(self, challenge_id: str) -> None:
        with self._get_connection() as conn:
            conn.execute("UPDATE otp_challenges SET verified = 1 WHERE challenge_id = ?", (challenge_id,))
            conn.commit()

    # --- Password Reset Tokens CRUD ---

    def create_password_reset_token(self, email: str) -> str:
        clean_email = email.strip().lower()
        now = time.time()
        expires_at = now + 600  # 10 minutes
        reset_token = f"rst_{os.urandom(16).hex()}"

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO password_reset_tokens (reset_token, email, created_at, expires_at, used)
                VALUES (?, ?, ?, ?, 0)
                """,
                (reset_token, clean_email, now, expires_at)
            )
            conn.commit()

        return reset_token

    def get_password_reset_token(self, reset_token: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM password_reset_tokens WHERE reset_token = ?",
                (reset_token,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

    def mark_password_reset_token_used(self, reset_token: str) -> None:
        with self._get_connection() as conn:
            conn.execute("UPDATE password_reset_tokens SET used = 1 WHERE reset_token = ?", (reset_token,))
            conn.commit()

    # --- Registration Verification Tokens CRUD ---

    def create_registration_token(self, email: str, username: str) -> str:
        clean_email = email.strip().lower()
        clean_username = username.strip().lower()
        now = time.time()
        expires_at = now + 900  # 15 minutes
        verification_token = f"reg_{os.urandom(16).hex()}"

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO registration_verification_tokens (verification_token, email, username, created_at, expires_at, used)
                VALUES (?, ?, ?, ?, ?, 0)
                """,
                (verification_token, clean_email, clean_username, now, expires_at)
            )
            conn.commit()

        return verification_token

    def get_valid_registration_token(self, verification_token: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM registration_verification_tokens WHERE verification_token = ?",
                (verification_token,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            token_data = dict(row)
            if token_data.get("used") == 1 or time.time() > token_data.get("expires_at", 0):
                return None
            return token_data

    def mark_registration_token_used(self, verification_token: str) -> None:
        with self._get_connection() as conn:
            conn.execute("UPDATE registration_verification_tokens SET used = 1 WHERE verification_token = ?", (verification_token,))
            conn.commit()

identity_storage = SQLiteIdentityStorage()

