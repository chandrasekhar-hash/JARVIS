import os
import sqlite3
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("JARVIS_KeyMetadataManager")


class KeyMetadataManager:
    """
    SQLite Metadata Manager for Keystore Metadata.
    Tracks key algorithm, public key fingerprint, creation time, rotation count, and migration status.
    Uses logs/jarvis_memory.db.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = db_path
        else:
            log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../logs"))
            os.makedirs(log_dir, exist_ok=True)
            self.db_path = os.path.join(log_dir, "jarvis_memory.db")

        self._memory_conn = None
        if self.db_path == ":memory:":
            self._memory_conn = sqlite3.connect(":memory:")
            self._memory_conn.row_factory = sqlite3.Row

        self._init_db()

    def _get_connection(self):
        if self._memory_conn:
            return self._memory_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS keystore_metadata (
                key_id TEXT PRIMARY KEY,
                algorithm TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                created_at REAL NOT NULL,
                rotation_count INTEGER NOT NULL DEFAULT 0,
                migration_status TEXT NOT NULL,
                provider_type TEXT NOT NULL
            )
        """)
        conn.commit()
        if not self._memory_conn:
            conn.close()

    def save_metadata(
        self,
        key_id: str,
        fingerprint: str,
        migration_status: str,
        provider_type: str,
        algorithm: str = "Ed25519",
        rotation_count: int = 0
    ):
        now = time.time()
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO keystore_metadata (
                key_id, algorithm, fingerprint, created_at, rotation_count, migration_status, provider_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(key_id) DO UPDATE SET
                fingerprint = excluded.fingerprint,
                rotation_count = excluded.rotation_count,
                migration_status = excluded.migration_status,
                provider_type = excluded.provider_type
        """, (key_id, algorithm, fingerprint, now, rotation_count, migration_status, provider_type))
        conn.commit()
        if not self._memory_conn:
            conn.close()

    def get_metadata(self, key_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM keystore_metadata WHERE key_id = ?", (key_id,))
        row = cursor.fetchone()
        if not self._memory_conn:
            conn.close()
        if not row:
            return None
        return {
            "key_id": row["key_id"],
            "algorithm": row["algorithm"],
            "fingerprint": row["fingerprint"],
            "created_at": row["created_at"],
            "rotation_count": row["rotation_count"],
            "migration_status": row["migration_status"],
            "provider_type": row["provider_type"]
        }


key_metadata_manager = KeyMetadataManager()
