import time
import json
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from database.connection import db_manager

logger = logging.getLogger("JARVIS_Cloud_Checkpoint")


class CheckpointMetadata(BaseModel):
    user_id: str
    device_id: str
    vector_clock: Dict[str, int] = Field(default_factory=dict)
    last_sequence_number: int = 0
    last_stream_id: str = "0-0"
    timestamp: float = Field(default_factory=time.time)


class CheckpointManager:
    """
    Standardized Checkpoint Manager tracking device vector clocks and stream watermarks in SQLite/PostgreSQL.
    """

    def __init__(self):
        self._init_table()

    def _init_table(self):
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cloud_sync_checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    vector_clock_json TEXT NOT NULL,
                    last_sequence_number INTEGER NOT NULL,
                    last_stream_id TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
            """)
            conn.commit()

    def save_checkpoint(self, checkpoint: CheckpointMetadata) -> CheckpointMetadata:
        chk_id = f"chk_{checkpoint.user_id}_{checkpoint.device_id}"
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cloud_sync_checkpoints (
                    checkpoint_id, user_id, device_id, vector_clock_json,
                    last_sequence_number, last_stream_id, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(checkpoint_id) DO UPDATE SET
                    vector_clock_json = excluded.vector_clock_json,
                    last_sequence_number = excluded.last_sequence_number,
                    last_stream_id = excluded.last_stream_id,
                    timestamp = excluded.timestamp
            """, (
                chk_id,
                checkpoint.user_id,
                checkpoint.device_id,
                json.dumps(checkpoint.vector_clock),
                checkpoint.last_sequence_number,
                checkpoint.last_stream_id,
                checkpoint.timestamp
            ))
            conn.commit()
        return checkpoint

    def get_checkpoint(self, user_id: str, device_id: str) -> Optional[CheckpointMetadata]:
        chk_id = f"chk_{user_id}_{device_id}"
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cloud_sync_checkpoints WHERE checkpoint_id = ?", (chk_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return CheckpointMetadata(
                user_id=row["user_id"],
                device_id=row["device_id"],
                vector_clock=json.loads(row["vector_clock_json"]) if row["vector_clock_json"] else {},
                last_sequence_number=row["last_sequence_number"],
                last_stream_id=row["last_stream_id"],
                timestamp=row["timestamp"]
            )


checkpoint_manager = CheckpointManager()
