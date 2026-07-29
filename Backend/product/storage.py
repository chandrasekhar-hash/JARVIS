"""
SQLite Storage Engine for J.A.R.V.I.S. Product Layer (Phase P1.1).
Implements thread-safe SQLite persistence for users, profiles, sessions, preferences, reset tokens,
schema versioning metadata, and append-only security audit logs.
"""
import os
import json
import sqlite3
import time
import logging
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager

from .config import ProductConfig, product_config
from .models import (
    User,
    Role,
    AccountStatus,
    UserProfile,
    UserPreferences,
    VoiceSettings,
    NotificationSettings,
    PrivacySettings,
    Session,
    PasswordResetToken,
)
from .audit import AuditEntry
from .interfaces import (
    IUserRepository,
    IProfileRepository,
    ISessionRepository,
    IPreferenceRepository,
    IPasswordResetRepository,
    IAuditRepository,
)

logger = logging.getLogger("JARVIS_ProductStorage")


class SQLiteProductStorage(
    IUserRepository,
    IProfileRepository,
    ISessionRepository,
    IPreferenceRepository,
    IPasswordResetRepository,
    IAuditRepository,
):
    """
    SQLite persistence implementation for all Phase P1.1 Product Layer domain models.
    Supports schema versioning, in-memory mode, WAL mode, automatic table creation, and connection safety.
    """

    def __init__(self, db_path: Optional[str] = None, config: Optional[ProductConfig] = None):
        self.config = config or product_config
        self.db_path = db_path or self.config.db_path
        self._shared_conn: Optional[sqlite3.Connection] = None
        if self.db_path == ":memory:":
            self._shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._shared_conn.row_factory = sqlite3.Row
        else:
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connection and transaction handling."""
        if self._shared_conn:
            try:
                yield self._shared_conn
                self._shared_conn.commit()
            except Exception as e:
                self._shared_conn.rollback()
                logger.error(f"[SQLiteProductStorage] Database transaction error: {e}")
                raise e
        else:
            conn = sqlite3.connect(self.db_path, timeout=self.config.db_timeout_seconds)
            conn.row_factory = sqlite3.Row
            if self.config.enable_wal_mode:
                conn.execute("PRAGMA journal_mode=WAL;")
            try:
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"[SQLiteProductStorage] Database transaction error: {e}")
                raise e
            finally:
                conn.close()

    def _init_db(self) -> None:
        """Initializes relational table schema and schema metadata."""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS schema_metadata (
                    schema_version INTEGER PRIMARY KEY,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    role TEXT DEFAULT 'USER',
                    status TEXT NOT NULL,
                    failed_login_attempts INTEGER DEFAULT 0,
                    locked_until REAL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    avatar TEXT DEFAULT '',
                    language_preference TEXT DEFAULT 'en-US',
                    time_zone TEXT DEFAULT 'UTC',
                    theme_preference TEXT DEFAULT 'dark',
                    account_creation_date REAL NOT NULL,
                    last_login REAL,
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT PRIMARY KEY,
                    voice_id TEXT DEFAULT 'en-US-Neural',
                    speech_rate REAL DEFAULT 1.0,
                    speech_pitch REAL DEFAULT 1.0,
                    wake_word TEXT DEFAULT 'JARVIS',
                    assistant_name TEXT DEFAULT 'J.A.R.V.I.S.',
                    preferred_ai_model TEXT DEFAULT 'gemini-2.5-flash',
                    preferred_language TEXT DEFAULT 'en-US',
                    mute_audio INTEGER DEFAULT 0,
                    audio_chimes INTEGER DEFAULT 1,
                    os_popups INTEGER DEFAULT 1,
                    cloud_telemetry INTEGER DEFAULT 0,
                    privacy_level TEXT DEFAULT 'standard',
                    updated_at REAL NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    remember_me_token TEXT UNIQUE,
                    device_id TEXT DEFAULT 'default_device',
                    device_name TEXT DEFAULT 'Desktop Client',
                    ip_address TEXT DEFAULT '127.0.0.1',
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    last_accessed_at REAL NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    token_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_hash TEXT UNIQUE NOT NULL,
                    expires_at REAL NOT NULL,
                    created_at REAL NOT NULL,
                    used INTEGER DEFAULT 0,
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS audit_logs (
                    audit_id TEXT PRIMARY KEY,
                    timestamp REAL NOT NULL,
                    user_id TEXT,
                    session_id TEXT,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    device_id TEXT,
                    ip_address TEXT,
                    result TEXT NOT NULL,
                    metadata TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
                CREATE INDEX IF NOT EXISTS idx_sessions_remember ON sessions(remember_me_token);
                CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
                CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_logs(user_id);
                CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_logs(event_type);
            """)

            # Initialize schema version metadata if absent
            row = conn.execute("SELECT schema_version FROM schema_metadata LIMIT 1").fetchone()
            if not row:
                now = time.time()
                conn.execute(
                    "INSERT INTO schema_metadata (schema_version, created_at, updated_at) VALUES (?, ?, ?)",
                    (1, now, now),
                )

    def get_schema_version(self) -> int:
        """Retrieves current SQLite database schema version."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT schema_version FROM schema_metadata LIMIT 1").fetchone()
            if row:
                return row["schema_version"]
        return 1

    # -------------------------------------------------------------------------
    # IUserRepository Implementation
    # -------------------------------------------------------------------------
    def create_user(self, user: User) -> User:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO users (user_id, username, email, password_hash, salt, role, status, failed_login_attempts, locked_until, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user.user_id,
                    user.username,
                    user.email,
                    user.password_hash,
                    user.salt,
                    user.role.value if isinstance(user.role, Role) else str(user.role),
                    user.status.value if isinstance(user.status, AccountStatus) else str(user.status),
                    user.failed_login_attempts,
                    user.locked_until,
                    user.created_at,
                    user.updated_at,
                ),
            )
        return user

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if row:
                return self._row_to_user(row)
        return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username.strip(),)).fetchone()
            if row:
                return self._row_to_user(row)
        return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email.strip(),)).fetchone()
            if row:
                return self._row_to_user(row)
        return None

    def update_user(self, user: User) -> User:
        user.updated_at = time.time()
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE users
                SET username = ?, email = ?, password_hash = ?, salt = ?, role = ?, status = ?,
                    failed_login_attempts = ?, locked_until = ?, updated_at = ?
                WHERE user_id = ?
                """,
                (
                    user.username,
                    user.email,
                    user.password_hash,
                    user.salt,
                    user.role.value if isinstance(user.role, Role) else str(user.role),
                    user.status.value if isinstance(user.status, AccountStatus) else str(user.status),
                    user.failed_login_attempts,
                    user.locked_until,
                    user.updated_at,
                    user.user_id,
                ),
            )
        return user

    def delete_user(self, user_id: str) -> bool:
        with self._get_connection() as conn:
            res = conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            return res.rowcount > 0

    def _row_to_user(self, row: sqlite3.Row) -> User:
        role_val = row["role"] if "role" in row.keys() and row["role"] else "USER"
        return User(
            user_id=row["user_id"],
            username=row["username"],
            email=row["email"],
            password_hash=row["password_hash"],
            salt=row["salt"],
            role=Role(role_val) if role_val in Role.__members__ else Role.USER,
            status=AccountStatus(row["status"]),
            failed_login_attempts=row["failed_login_attempts"],
            locked_until=row["locked_until"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    # -------------------------------------------------------------------------
    # IProfileRepository Implementation
    # -------------------------------------------------------------------------
    def create_profile(self, profile: UserProfile) -> UserProfile:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO user_profiles (user_id, username, display_name, email, avatar, language_preference, time_zone, theme_preference, account_creation_date, last_login)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile.user_id,
                    profile.username,
                    profile.display_name,
                    profile.email,
                    profile.avatar,
                    profile.language_preference,
                    profile.time_zone,
                    profile.theme_preference,
                    profile.account_creation_date,
                    profile.last_login,
                ),
            )
        return profile

    def get_profile_by_user_id(self, user_id: str) -> Optional[UserProfile]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)).fetchone()
            if row:
                return UserProfile(
                    user_id=row["user_id"],
                    username=row["username"],
                    display_name=row["display_name"],
                    email=row["email"],
                    avatar=row["avatar"],
                    language_preference=row["language_preference"],
                    time_zone=row["time_zone"],
                    theme_preference=row["theme_preference"],
                    account_creation_date=row["account_creation_date"],
                    last_login=row["last_login"],
                )
        return None

    def update_profile(self, profile: UserProfile) -> UserProfile:
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE user_profiles
                SET username = ?, display_name = ?, email = ?, avatar = ?,
                    language_preference = ?, time_zone = ?, theme_preference = ?, last_login = ?
                WHERE user_id = ?
                """,
                (
                    profile.username,
                    profile.display_name,
                    profile.email,
                    profile.avatar,
                    profile.language_preference,
                    profile.time_zone,
                    profile.theme_preference,
                    profile.last_login,
                    profile.user_id,
                ),
            )
        return profile

    def delete_profile(self, user_id: str) -> bool:
        with self._get_connection() as conn:
            res = conn.execute("DELETE FROM user_profiles WHERE user_id = ?", (user_id,))
            return res.rowcount > 0

    # -------------------------------------------------------------------------
    # ISessionRepository Implementation
    # -------------------------------------------------------------------------
    def create_session(self, session: Session) -> Session:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions (session_id, user_id, token, remember_me_token, device_id, device_name, ip_address, created_at, expires_at, last_accessed_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.session_id,
                    session.user_id,
                    session.token,
                    session.remember_me_token,
                    session.device_id,
                    session.device_name,
                    session.ip_address,
                    session.created_at,
                    session.expires_at,
                    session.last_accessed_at,
                    1 if session.is_active else 0,
                ),
            )
        return session

    def get_session_by_token(self, token: str) -> Optional[Session]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE token = ? AND is_active = 1", (token,)).fetchone()
            if row:
                return self._row_to_session(row)
        return None

    def get_session_by_id(self, session_id: str) -> Optional[Session]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
            if row:
                return self._row_to_session(row)
        return None

    def get_session_by_remember_token(self, remember_me_token: str) -> Optional[Session]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE remember_me_token = ? AND is_active = 1", (remember_me_token,)).fetchone()
            if row:
                return self._row_to_session(row)
        return None

    def get_user_sessions(self, user_id: str) -> List[Session]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM sessions WHERE user_id = ? AND is_active = 1 ORDER BY last_accessed_at DESC", (user_id,)).fetchall()
            return [self._row_to_session(r) for r in rows]

    def update_session(self, session: Session) -> Session:
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE sessions
                SET expires_at = ?, last_accessed_at = ?, is_active = ?
                WHERE session_id = ?
                """,
                (
                    session.expires_at,
                    session.last_accessed_at,
                    1 if session.is_active else 0,
                    session.session_id,
                ),
            )
        return session

    def revoke_session(self, session_id: str) -> bool:
        with self._get_connection() as conn:
            res = conn.execute("UPDATE sessions SET is_active = 0 WHERE session_id = ?", (session_id,))
            return res.rowcount > 0

    def revoke_all_user_sessions(self, user_id: str) -> int:
        with self._get_connection() as conn:
            res = conn.execute("UPDATE sessions SET is_active = 0 WHERE user_id = ?", (user_id,))
            return res.rowcount

    def _row_to_session(self, row: sqlite3.Row) -> Session:
        return Session(
            session_id=row["session_id"],
            user_id=row["user_id"],
            token=row["token"],
            remember_me_token=row["remember_me_token"],
            device_id=row["device_id"],
            device_name=row["device_name"],
            ip_address=row["ip_address"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            last_accessed_at=row["last_accessed_at"],
            is_active=bool(row["is_active"]),
        )

    # -------------------------------------------------------------------------
    # IPreferenceRepository Implementation
    # -------------------------------------------------------------------------
    def create_preferences(self, preferences: UserPreferences) -> UserPreferences:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO user_preferences (
                    user_id, voice_id, speech_rate, speech_pitch, wake_word, assistant_name,
                    preferred_ai_model, preferred_language, mute_audio, audio_chimes,
                    os_popups, cloud_telemetry, privacy_level, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    preferences.user_id,
                    preferences.voice_settings.voice_id,
                    preferences.voice_settings.speech_rate,
                    preferences.voice_settings.speech_pitch,
                    preferences.wake_word,
                    preferences.assistant_name,
                    preferences.preferred_ai_model,
                    preferences.preferred_language,
                    1 if preferences.notification_settings.mute_audio else 0,
                    1 if preferences.notification_settings.audio_chimes else 0,
                    1 if preferences.notification_settings.os_popups else 0,
                    1 if preferences.privacy_settings.cloud_telemetry else 0,
                    preferences.privacy_settings.privacy_level,
                    preferences.updated_at,
                ),
            )
        return preferences

    def get_preferences_by_user_id(self, user_id: str) -> Optional[UserPreferences]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM user_preferences WHERE user_id = ?", (user_id,)).fetchone()
            if row:
                return UserPreferences(
                    user_id=row["user_id"],
                    voice_settings=VoiceSettings(
                        voice_id=row["voice_id"],
                        speech_rate=row["speech_rate"],
                        speech_pitch=row["speech_pitch"],
                    ),
                    wake_word=row["wake_word"],
                    assistant_name=row["assistant_name"],
                    preferred_ai_model=row["preferred_ai_model"],
                    preferred_language=row["preferred_language"],
                    notification_settings=NotificationSettings(
                        mute_audio=bool(row["mute_audio"]),
                        audio_chimes=bool(row["audio_chimes"]),
                        os_popups=bool(row["os_popups"]),
                    ),
                    privacy_settings=PrivacySettings(
                        cloud_telemetry=bool(row["cloud_telemetry"]),
                        privacy_level=row["privacy_level"],
                    ),
                    updated_at=row["updated_at"],
                )
        return None

    def update_preferences(self, preferences: UserPreferences) -> UserPreferences:
        preferences.updated_at = time.time()
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE user_preferences
                SET voice_id = ?, speech_rate = ?, speech_pitch = ?, wake_word = ?,
                    assistant_name = ?, preferred_ai_model = ?, preferred_language = ?,
                    mute_audio = ?, audio_chimes = ?, os_popups = ?,
                    cloud_telemetry = ?, privacy_level = ?, updated_at = ?
                WHERE user_id = ?
                """,
                (
                    preferences.voice_settings.voice_id,
                    preferences.voice_settings.speech_rate,
                    preferences.voice_settings.speech_pitch,
                    preferences.wake_word,
                    preferences.assistant_name,
                    preferences.preferred_ai_model,
                    preferences.preferred_language,
                    1 if preferences.notification_settings.mute_audio else 0,
                    1 if preferences.notification_settings.audio_chimes else 0,
                    1 if preferences.notification_settings.os_popups else 0,
                    1 if preferences.privacy_settings.cloud_telemetry else 0,
                    preferences.privacy_settings.privacy_level,
                    preferences.updated_at,
                    preferences.user_id,
                ),
            )
        return preferences

    def delete_preferences(self, user_id: str) -> bool:
        with self._get_connection() as conn:
            res = conn.execute("DELETE FROM user_preferences WHERE user_id = ?", (user_id,))
            return res.rowcount > 0

    # -------------------------------------------------------------------------
    # IPasswordResetRepository Implementation
    # -------------------------------------------------------------------------
    def create_reset_token(self, token: PasswordResetToken) -> PasswordResetToken:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO password_reset_tokens (token_id, user_id, token_hash, expires_at, created_at, used)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    token.token_id,
                    token.user_id,
                    token.token_hash,
                    token.expires_at,
                    token.created_at,
                    1 if token.used else 0,
                ),
            )
        return token

    def get_reset_token(self, token_hash: str) -> Optional[PasswordResetToken]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM password_reset_tokens WHERE token_hash = ?", (token_hash,)).fetchone()
            if row:
                return PasswordResetToken(
                    token_id=row["token_id"],
                    user_id=row["user_id"],
                    token_hash=row["token_hash"],
                    expires_at=row["expires_at"],
                    created_at=row["created_at"],
                    used=bool(row["used"]),
                )
        return None

    def mark_reset_token_used(self, token_id: str) -> bool:
        with self._get_connection() as conn:
            res = conn.execute("UPDATE password_reset_tokens SET used = 1 WHERE token_id = ?", (token_id,))
            return res.rowcount > 0

    # -------------------------------------------------------------------------
    # IAuditRepository Implementation
    # -------------------------------------------------------------------------
    def log_audit_entry(self, entry: AuditEntry) -> AuditEntry:
        metadata_str = json.dumps(entry.metadata) if entry.metadata else "{}"
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO audit_logs (
                    audit_id, timestamp, user_id, session_id, event_type, severity,
                    device_id, ip_address, result, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.audit_id,
                    entry.timestamp,
                    entry.user_id,
                    entry.session_id,
                    entry.event_type,
                    entry.severity,
                    entry.device_id,
                    entry.ip_address,
                    entry.result,
                    metadata_str,
                ),
            )
        return entry

    def query_audit_logs(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditEntry]:
        sql = "SELECT * FROM audit_logs WHERE 1=1"
        params: List[Any] = []

        if user_id:
            sql += " AND user_id = ?"
            params.append(user_id)
        if event_type:
            sql += " AND event_type = ?"
            params.append(event_type)

        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
            entries: List[AuditEntry] = []
            for r in rows:
                meta = json.loads(r["metadata"]) if r["metadata"] else {}
                entries.append(
                    AuditEntry(
                        audit_id=r["audit_id"],
                        timestamp=r["timestamp"],
                        user_id=r["user_id"],
                        session_id=r["session_id"],
                        event_type=r["event_type"],
                        severity=r["severity"],
                        device_id=r["device_id"],
                        ip_address=r["ip_address"],
                        result=r["result"],
                        metadata=meta,
                    )
                )
            return entries
