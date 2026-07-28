import os
import sqlite3
import logging
from typing import Optional
from Cloud.config.settings import cloud_settings
from Cloud.database.schema_verifier import schema_verifier

logger = logging.getLogger("JARVIS_CloudDatabaseManager")

CLOUD_SCHEMA_VERSION = "v1_cloud_backend"


class CloudDatabaseManager:
    """
    Cloud Database Manager managing connections for PostgreSQL / SQLite.
    Schema initialization & migrations are driven strictly by Alembic & SchemaVerifier.
    Zero runtime DDL (CREATE TABLE IF NOT EXISTS) statements.
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
        """
        Application startup database verification.
        Executes SchemaVerifier to check schema compatibility, pre-validate legacy DBs,
        and manage Alembic migration status without runtime DDL statements.
        """
        success, msg = schema_verifier.apply_or_verify_migrations()
        if not success:
            logger.critical(f"Database initialization halted: {msg}")


db_manager = CloudDatabaseManager()
