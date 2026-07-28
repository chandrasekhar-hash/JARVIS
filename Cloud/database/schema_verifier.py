import os
import sqlite3
import logging
from typing import Dict, Any, Optional, Tuple
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic import command
from Cloud.config.settings import cloud_settings
from Cloud.database.migration_lock import MigrationLockManager

logger = logging.getLogger("JARVIS_SchemaVerifier")


class SchemaVerifier:
    """
    Schema Compatibility Verifier & Pre-Stamping Legacy Validator.
    Verifies database connectivity, dynamically retrieves head revision from Alembic ScriptDirectory,
    validates legacy tables before stamping, and enforces non-automatic production startup.
    """

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or cloud_settings.database_url
        self.alembic_ini_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../alembic.ini"))
        self.lock_mgr = MigrationLockManager(self.db_url)

    def _resolve_db_path(self) -> str:
        if self.db_url.startswith("sqlite:///"):
            path = self.db_url.replace("sqlite:///", "")
            if os.path.isabs(path):
                return path
            return os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", path))
        return os.path.abspath("logs/jarvis_cloud_dev.db")

    def _get_alembic_config(self) -> Config:
        cfg = Config(self.alembic_ini_path)
        cfg.set_main_option("script_location", os.path.abspath(os.path.join(os.path.dirname(__file__), "../alembic")))
        cfg.set_main_option("sqlalchemy.url", self.db_url)
        return cfg

    def get_expected_head_revision(self) -> str:
        """
        Dynamically retrieves the current head revision from Alembic ScriptDirectory.
        """
        cfg = self._get_alembic_config()
        script = ScriptDirectory.from_config(cfg)
        head_rev = script.get_current_head()
        if not head_rev:
            raise RuntimeError("Failed to resolve head revision from Alembic migration directory.")
        return head_rev

    def validate_legacy_schema(self, conn: sqlite3.Connection) -> bool:
        """
        Validates existing legacy database tables against expected baseline models.
        Must match cloud_users, cloud_devices, cloud_sessions, cloud_audit_logs, cloud_configurations.
        """
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = set(row[0] for row in cursor.fetchall())
        required_tables = {"cloud_users", "cloud_devices", "cloud_sessions", "cloud_audit_logs", "cloud_configurations"}

        if not required_tables.issubset(tables):
            missing = required_tables - tables
            logger.error(f"Legacy schema validation failed! Missing required tables: {missing}")
            return False

        logger.info("Legacy schema validation successful! Database schema matches baseline.")
        return True

    def get_current_revision(self) -> Optional[str]:
        """
        Retrieves current revision string from alembic_version table.
        """
        try:
            abs_path = self._resolve_db_path()
            if not os.path.exists(abs_path):
                return None
            conn = sqlite3.connect(abs_path)
            cursor = conn.cursor()
            cursor.execute("SELECT version_num FROM alembic_version")
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else None
        except Exception:
            pass
        return None

    def apply_or_verify_migrations(self) -> Tuple[bool, str]:
        """
        Main application startup entrypoint.
        1. Checks if database connection is reachable.
        2. Detects legacy database & validates schema before stamping baseline.
        3. Enforces non-automatic production migration policy.
        """
        is_prod = os.getenv("ENVIRONMENT", "development").lower() == "production"
        alembic_cfg = self._get_alembic_config()
        expected_head = self.get_expected_head_revision()

        curr_rev = self.get_current_revision()

        # Handle legacy or uninitialized database
        if not curr_rev:
            abs_path = self._resolve_db_path()
            db_exists = os.path.exists(abs_path)

            if db_exists:
                conn = sqlite3.connect(abs_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cloud_schema_version'")
                has_legacy = cursor.fetchone() is not None

                if has_legacy:
                    logger.info("Detected legacy runtime-DDL database ('cloud_schema_version'). Validating schema before stamping...")
                    if not self.validate_legacy_schema(conn):
                        conn.close()
                        msg = "FATAL: Legacy database schema mismatch! Aborting migration to protect data."
                        logger.critical(msg)
                        return False, msg
                    conn.close()

                    # Stamp baseline revision dynamically
                    if self.lock_mgr.acquire_lock():
                        try:
                            logger.info(f"Stamping baseline revision '{expected_head}'...")
                            command.stamp(alembic_cfg, expected_head)
                            curr_rev = expected_head
                        finally:
                            self.lock_mgr.release_lock()
                else:
                    conn.close()

        # Non-automatic Production startup policy
        if is_prod:
            curr_rev = self.get_current_revision()
            if curr_rev != expected_head:
                msg = (
                    f"PRODUCTION STARTUP HALTED: Database schema revision '{curr_rev}' does not match "
                    f"expected application revision '{expected_head}'. "
                    f"Please run 'alembic upgrade head' manually before starting Cloud API Gateway."
                )
                logger.critical(msg)
                return False, msg
            logger.info(f"Production Schema Verified (Revision '{curr_rev}').")
            return True, "Schema verified"

        # Development Mode: Automatic upgrade if needed
        curr_rev = self.get_current_revision()
        if curr_rev != expected_head:
            if self.lock_mgr.acquire_lock():
                try:
                    logger.info(f"Development Mode: Running 'alembic upgrade head' to reach revision '{expected_head}'...")
                    command.upgrade(alembic_cfg, "head")
                finally:
                    self.lock_mgr.release_lock()

        return True, "Schema ready"


schema_verifier = SchemaVerifier()
EXPECTED_HEAD_REVISION = schema_verifier.get_expected_head_revision()
