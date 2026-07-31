"""
JARVIS Product 1.7 - Execution History Store.
Logs workflow execution runs, step logs, run status, and tracebacks to SQLite.
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from .interfaces import IExecutionHistoryStore
from .models import WorkflowRunRecord, RunStatus, TriggerType

logger = logging.getLogger(__name__)


class SQLiteExecutionHistoryStore(IExecutionHistoryStore):
    def __init__(self, db_path: str = "logs/jarvis_automation.db"):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        conn = self._get_connection()
        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS automation_runs (
                        run_id TEXT PRIMARY KEY,
                        workflow_id TEXT NOT NULL,
                        workflow_name TEXT NOT NULL,
                        owner TEXT NOT NULL,
                        trigger_type TEXT NOT NULL,
                        start_time TEXT NOT NULL,
                        end_time TEXT,
                        duration_ms REAL DEFAULT 0.0,
                        status TEXT NOT NULL,
                        steps_completed INTEGER DEFAULT 0,
                        total_steps INTEGER DEFAULT 0,
                        error_details TEXT,
                        step_logs_json TEXT
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_wf_id ON automation_runs(workflow_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_owner ON automation_runs(owner);")
        finally:
            conn.close()

    def save_run_record(self, record: WorkflowRunRecord) -> bool:
        conn = self._get_connection()
        try:
            with conn:
                end_iso = record.end_time.isoformat() if record.end_time else None
                conn.execute(
                    """
                    INSERT OR REPLACE INTO automation_runs (
                        run_id, workflow_id, workflow_name, owner, trigger_type,
                        start_time, end_time, duration_ms, status, steps_completed,
                        total_steps, error_details, step_logs_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.run_id,
                        record.workflow_id,
                        record.workflow_name,
                        record.owner,
                        record.trigger_type.value,
                        record.start_time.isoformat(),
                        end_iso,
                        record.duration_ms,
                        record.status.value,
                        record.steps_completed,
                        record.total_steps,
                        record.error_details,
                        record.step_logs_json,
                    ),
                )
            return True
        except Exception as e:
            logger.error(f"save_run_record error: {e}")
            return False
        finally:
            conn.close()

    def get_run_record(self, run_id: str) -> Optional[WorkflowRunRecord]:
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT * FROM automation_runs WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()
            return self._row_to_record(row) if row else None
        finally:
            conn.close()

    def list_run_records(
        self,
        workflow_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[WorkflowRunRecord]:
        conn = self._get_connection()
        try:
            query = "SELECT * FROM automation_runs WHERE 1=1"
            params = []
            if workflow_id:
                query += " AND workflow_id = ?"
                params.append(workflow_id)
            if owner_id:
                query += " AND owner = ?"
                params.append(owner_id)
            query += " ORDER BY start_time DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_record(r) for r in rows]
        finally:
            conn.close()

    def _row_to_record(self, row: sqlite3.Row) -> WorkflowRunRecord:
        end_time = datetime.fromisoformat(row["end_time"]) if row["end_time"] else None
        return WorkflowRunRecord(
            run_id=row["run_id"],
            workflow_id=row["workflow_id"],
            workflow_name=row["workflow_name"],
            owner=row["owner"],
            trigger_type=TriggerType(row["trigger_type"]),
            start_time=datetime.fromisoformat(row["start_time"]),
            end_time=end_time,
            duration_ms=row["duration_ms"],
            status=RunStatus(row["status"]),
            steps_completed=row["steps_completed"],
            total_steps=row["total_steps"],
            error_details=row["error_details"],
            step_logs_json=row["step_logs_json"],
        )
