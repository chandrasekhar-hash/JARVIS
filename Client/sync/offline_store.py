import os
import json
import time
import sqlite3
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("JARVIS_Client_OfflineStore")


class OfflineStore:
    """
    Persistent Client Offline Store (SQLite database at logs/client_sync.db or in-memory for testing).
    Stores client checkpoints, local CRDT snapshot cache, pending operations, and session credentials.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = db_path
        else:
            log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../logs"))
            os.makedirs(log_dir, exist_ok=True)
            self.db_path = os.path.join(log_dir, "client_sync.db")

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
        # Client Checkpoints Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS client_checkpoints (
                checkpoint_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                device_id TEXT NOT NULL,
                vector_clock_json TEXT NOT NULL,
                last_sequence_number INTEGER NOT NULL,
                last_stream_id TEXT NOT NULL,
                timestamp REAL NOT NULL
            )
        """)

        # Client Cached State Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS client_state_cache (
                entity_type TEXT PRIMARY KEY,
                snapshot_json TEXT NOT NULL,
                version INTEGER NOT NULL,
                timestamp REAL NOT NULL
            )
        """)

        # Client Pending Operations Buffer
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS client_pending_ops (
                op_id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                changes_json TEXT NOT NULL,
                sequence_number INTEGER NOT NULL,
                timestamp REAL NOT NULL,
                status TEXT NOT NULL
            )
        """)
        conn.commit()
        if not self._memory_conn:
            conn.close()

    def save_checkpoint(self, user_id: str, device_id: str, last_seq: int, stream_id: str = "0-0") -> Dict[str, Any]:
        chk_id = f"chk_client_{user_id}_{device_id}"
        now = time.time()
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO client_checkpoints (
                checkpoint_id, user_id, device_id, vector_clock_json,
                last_sequence_number, last_stream_id, timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(checkpoint_id) DO UPDATE SET
                last_sequence_number = excluded.last_sequence_number,
                last_stream_id = excluded.last_stream_id,
                timestamp = excluded.timestamp
        """, (chk_id, user_id, device_id, "{}", last_seq, stream_id, now))
        conn.commit()
        if not self._memory_conn:
            conn.close()
        return {"user_id": user_id, "device_id": device_id, "last_sequence_number": last_seq, "timestamp": now}

    def get_checkpoint(self, user_id: str, device_id: str) -> Optional[Dict[str, Any]]:
        chk_id = f"chk_client_{user_id}_{device_id}"
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM client_checkpoints WHERE checkpoint_id = ?", (chk_id,))
        row = cursor.fetchone()
        if not self._memory_conn:
            conn.close()
        if not row:
            return None
        return {
            "user_id": row["user_id"],
            "device_id": row["device_id"],
            "last_sequence_number": row["last_sequence_number"],
            "last_stream_id": row["last_stream_id"],
            "timestamp": row["timestamp"]
        }

    def save_entity_cache(self, entity_type: str, snapshot: Dict[str, Any], version: int = 1):
        now = time.time()
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO client_state_cache (entity_type, snapshot_json, version, timestamp)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(entity_type) DO UPDATE SET
                snapshot_json = excluded.snapshot_json,
                version = excluded.version,
                timestamp = excluded.timestamp
        """, (entity_type, json.dumps(snapshot), version, now))
        conn.commit()
        if not self._memory_conn:
            conn.close()

    def get_entity_cache(self, entity_type: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT snapshot_json FROM client_state_cache WHERE entity_type = ?", (entity_type,))
        row = cursor.fetchone()
        if not self._memory_conn:
            conn.close()
        if not row:
            return None
        return json.loads(row["snapshot_json"])

    def save_pending_op(self, op: Dict[str, Any]):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO client_pending_ops (op_id, entity_type, changes_json, sequence_number, timestamp, status)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(op_id) DO UPDATE SET
                status = excluded.status
        """, (
            op["message_id"],
            op["entity_type"],
            json.dumps(op["changes"]),
            op["sequence_number"],
            op.get("timestamp", time.time()),
            op.get("status", "pending")
        ))
        conn.commit()
        if not self._memory_conn:
            conn.close()

    def get_all_pending_ops(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM client_pending_ops ORDER BY sequence_number ASC, timestamp ASC")
        rows = cursor.fetchall()
        if not self._memory_conn:
            conn.close()
        ops = []
        for r in rows:
            ops.append({
                "message_id": r["op_id"],
                "entity_type": r["entity_type"],
                "changes": json.loads(r["changes_json"]),
                "sequence_number": r["sequence_number"],
                "timestamp": r["timestamp"],
                "status": r["status"]
            })
        return ops

    def remove_pending_op(self, op_id: str):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM client_pending_ops WHERE op_id = ?", (op_id,))
        conn.commit()
        if not self._memory_conn:
            conn.close()

    def clear_pending_ops(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM client_pending_ops")
        conn.commit()
        if not self._memory_conn:
            conn.close()


offline_store = OfflineStore()
