import os
import sqlite3
import json
import time
from typing import List, Optional, Dict, Any
from autonomous.scheduler_models import (
    ScheduledJob,
    JobExecutionRecord,
    ScheduleTrigger,
    JobStatus,
    JobType,
    SchedulerMetrics
)
from tools.telemetry import log_structured, backend_log

class SQLiteSchedulerStorage:
    """
    Persistent SQLite storage driver for scheduled jobs and execution history.
    Integrates into the primary project database at logs/jarvis_memory.db.
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
            # 1. scheduled_jobs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_jobs (
                    job_id TEXT PRIMARY KEY,
                    task_name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    trigger_json TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    last_run REAL,
                    next_run REAL NOT NULL,
                    status TEXT NOT NULL,
                    execution_count INTEGER NOT NULL DEFAULT 0,
                    failure_count INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 3,
                    retry_backoff_factor REAL NOT NULL DEFAULT 2.0,
                    timeout_seconds INTEGER NOT NULL DEFAULT 300,
                    params_json TEXT NOT NULL,
                    node_id TEXT NOT NULL DEFAULT 'local_node',
                    remote_origin TEXT,
                    plugin_id TEXT
                )
            """)

            # 2. job_executions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_executions (
                    execution_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    task_name TEXT NOT NULL,
                    start_time REAL NOT NULL,
                    end_time REAL,
                    duration_seconds REAL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    retry_attempt INTEGER NOT NULL DEFAULT 0,
                    result_summary TEXT,
                    FOREIGN KEY (job_id) REFERENCES scheduled_jobs (job_id) ON DELETE CASCADE
                )
            """)

            # 3. scheduler_settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scheduler_settings (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            conn.commit()
            log_structured(backend_log, "INFO", f"[SchedulerStorage] Initialized tables in {self.db_path}")

    def save_job(self, job: ScheduledJob) -> ScheduledJob:
        job.updated_at = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO scheduled_jobs (
                    job_id, task_name, description, trigger_json, enabled,
                    created_at, updated_at, last_run, next_run, status,
                    execution_count, failure_count, max_retries, retry_backoff_factor,
                    timeout_seconds, params_json, node_id, remote_origin, plugin_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    task_name=excluded.task_name,
                    description=excluded.description,
                    trigger_json=excluded.trigger_json,
                    enabled=excluded.enabled,
                    updated_at=excluded.updated_at,
                    last_run=excluded.last_run,
                    next_run=excluded.next_run,
                    status=excluded.status,
                    execution_count=excluded.execution_count,
                    failure_count=excluded.failure_count,
                    max_retries=excluded.max_retries,
                    retry_backoff_factor=excluded.retry_backoff_factor,
                    timeout_seconds=excluded.timeout_seconds,
                    params_json=excluded.params_json,
                    node_id=excluded.node_id,
                    remote_origin=excluded.remote_origin,
                    plugin_id=excluded.plugin_id
            """, (
                job.job_id, job.task_name, job.description,
                job.trigger.model_dump_json(), 1 if job.enabled else 0,
                job.created_at, job.updated_at, job.last_run, job.next_run, job.status.value,
                job.execution_count, job.failure_count, job.max_retries, job.retry_backoff_factor,
                job.timeout_seconds, json.dumps(job.params), job.node_id, job.remote_origin, job.plugin_id
            ))
            conn.commit()
        return job

    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scheduled_jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_job(row)

    def get_all_jobs(self) -> List[ScheduledJob]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scheduled_jobs ORDER BY next_run ASC")
            rows = cursor.fetchall()
            return [self._row_to_job(r) for r in rows]

    def delete_job(self, job_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM scheduled_jobs WHERE job_id = ?", (job_id,))
            conn.commit()
            return cursor.rowcount > 0

    def log_execution(self, record: JobExecutionRecord) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO job_executions (
                    execution_id, job_id, task_name, start_time, end_time,
                    duration_seconds, status, error_message, retry_attempt, result_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(execution_id) DO UPDATE SET
                    end_time=excluded.end_time,
                    duration_seconds=excluded.duration_seconds,
                    status=excluded.status,
                    error_message=excluded.error_message,
                    retry_attempt=excluded.retry_attempt,
                    result_summary=excluded.result_summary
            """, (
                record.execution_id, record.job_id, record.task_name, record.start_time,
                record.end_time, record.duration_seconds, record.status.value,
                record.error_message, record.retry_attempt, record.result_summary
            ))
            conn.commit()

    def get_job_history(self, job_id: str, limit: int = 50) -> List[JobExecutionRecord]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM job_executions WHERE job_id = ? ORDER BY start_time DESC LIMIT ?",
                (job_id, limit)
            )
            rows = cursor.fetchall()
            return [self._row_to_execution(r) for r in rows]

    def get_metrics(self) -> SchedulerMetrics:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM scheduled_jobs")
            tot = cursor.fetchone()["cnt"]

            cursor.execute("SELECT COUNT(*) as cnt FROM scheduled_jobs WHERE enabled = 1")
            en = cursor.fetchone()["cnt"]

            cursor.execute("SELECT COUNT(*) as cnt FROM scheduled_jobs WHERE status = ?", (JobStatus.RUNNING.value,))
            run = cursor.fetchone()["cnt"]

            cursor.execute("SELECT COUNT(*) as cnt FROM job_executions WHERE status = ?", (JobStatus.COMPLETED.value,))
            comp = cursor.fetchone()["cnt"]

            cursor.execute("SELECT COUNT(*) as cnt FROM job_executions WHERE status = ?", (JobStatus.FAILED.value,))
            fail = cursor.fetchone()["cnt"]

            cursor.execute("SELECT COUNT(*) as cnt FROM job_executions")
            tot_exec = cursor.fetchone()["cnt"]

            cursor.execute("SELECT AVG(duration_seconds) as avg_dur FROM job_executions WHERE duration_seconds IS NOT NULL")
            avg_dur = cursor.fetchone()["avg_dur"] or 0.0

            return SchedulerMetrics(
                total_jobs=tot,
                enabled_jobs=en,
                running_jobs=run,
                completed_jobs=comp,
                failed_jobs=fail,
                total_executions=tot_exec,
                average_duration_seconds=round(float(avg_dur), 3)
            )

    def _row_to_job(self, row: sqlite3.Row) -> ScheduledJob:
        tr_data = json.loads(row["trigger_json"])
        trigger = ScheduleTrigger(**tr_data)
        params = json.loads(row["params_json"]) if row["params_json"] else {}
        return ScheduledJob(
            job_id=row["job_id"],
            task_name=row["task_name"],
            description=row["description"],
            trigger=trigger,
            enabled=bool(row["enabled"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_run=row["last_run"],
            next_run=row["next_run"],
            status=JobStatus(row["status"]),
            execution_count=row["execution_count"],
            failure_count=row["failure_count"],
            max_retries=row["max_retries"],
            retry_backoff_factor=row["retry_backoff_factor"],
            timeout_seconds=row["timeout_seconds"],
            params=params,
            node_id=row["node_id"],
            remote_origin=row["remote_origin"],
            plugin_id=row["plugin_id"]
        )

    def _row_to_execution(self, row: sqlite3.Row) -> JobExecutionRecord:
        return JobExecutionRecord(
            execution_id=row["execution_id"],
            job_id=row["job_id"],
            task_name=row["task_name"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            duration_seconds=row["duration_seconds"],
            status=JobStatus(row["status"]),
            error_message=row["error_message"],
            retry_attempt=row["retry_attempt"],
            result_summary=row["result_summary"]
        )

scheduler_storage = SQLiteSchedulerStorage()
