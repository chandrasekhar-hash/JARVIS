import os
import json
import time
import uuid
import sqlite3
import asyncio
from typing import Dict, List, Optional, Any, Set
from pydantic import BaseModel, Field
from brain.event_bus import event_bus
from tools.telemetry import log_structured, backend_log
from autonomous.models import (
    Goal, Task, ExecutionPlan, ProgressSnapshot, ExecutionState, TaskResult, RecoveryAttempt, GoalStatus
)
from autonomous.interfaces import IWorkflowManager
from autonomous.config import autonomous_config


class FullWorkflowCheckpoint(BaseModel):
    """Immutable snapshot capturing complete workflow execution state."""
    checkpoint_id: str = Field(default_factory=lambda: f"chk_{uuid.uuid4().hex[:8]}")
    workflow_id: str
    goal_id: str
    version: str = Field(default_factory=lambda: autonomous_config.WORKFLOW_CHECKPOINT_VERSION)
    timestamp: float = Field(default_factory=time.time)
    goal: Goal
    plan: ExecutionPlan
    progress_snapshot: ProgressSnapshot
    task_states: Dict[str, ExecutionState] = Field(default_factory=dict)
    task_results: Dict[str, TaskResult] = Field(default_factory=dict)
    recovery_history: List[RecoveryAttempt] = Field(default_factory=list)
    execution_context: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowManager(IWorkflowManager):
    """Subsystem responsible for persistent workflow checkpointing, version validation, and state restoration."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
            os.makedirs(logs_dir, exist_ok=True)
            db_path = os.path.join(logs_dir, "jarvis_workflows.db")

        self.db_path = db_path
        self._lock = asyncio.Lock()
        self._init_db()

    def _init_db(self) -> None:
        """Initializes SQLite schema for workflows and checkpoints."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflows (
                    workflow_id TEXT PRIMARY KEY,
                    goal_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    archived INTEGER DEFAULT 0,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    checkpoint_data TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    FOREIGN KEY (workflow_id) REFERENCES workflows(workflow_id) ON DELETE CASCADE
                );
            """)
            conn.commit()

    # ── Version & Schema Validation ─────────────────────────────────────────────

    def validate_checkpoint(self, checkpoint_data_str: str) -> FullWorkflowCheckpoint:
        """Validates checkpoint JSON string against version rules and schema invariants."""
        try:
            raw_dict = json.loads(checkpoint_data_str)
        except Exception as e_json:
            event_bus.emit(autonomous_config.EVENT_CHECKPOINT_VALIDATION_FAILED, reason="Malformed JSON")
            raise ValueError(f"Corrupted checkpoint: Invalid JSON format ({str(e_json)}).")

        # Check version compatibility
        version = raw_dict.get("version")
        if version != autonomous_config.WORKFLOW_CHECKPOINT_VERSION:
            event_bus.emit(
                autonomous_config.EVENT_CHECKPOINT_VALIDATION_FAILED, 
                reason=f"Incompatible version '{version}' (Expected '{autonomous_config.WORKFLOW_CHECKPOINT_VERSION}')"
            )
            raise ValueError(
                f"Incompatible checkpoint version '{version}'. Expected '{autonomous_config.WORKFLOW_CHECKPOINT_VERSION}'."
            )

        # Validate required fields
        required_fields = ["checkpoint_id", "workflow_id", "goal_id", "goal", "plan", "progress_snapshot"]
        for field in required_fields:
            if field not in raw_dict:
                event_bus.emit(autonomous_config.EVENT_CHECKPOINT_VALIDATION_FAILED, reason=f"Missing field '{field}'")
                raise ValueError(f"Corrupted checkpoint: Missing required field '{field}'.")

        try:
            return FullWorkflowCheckpoint(**raw_dict)
        except Exception as e_pydantic:
            event_bus.emit(autonomous_config.EVENT_CHECKPOINT_VALIDATION_FAILED, reason=f"Pydantic schema validation error: {str(e_pydantic)}")
            raise ValueError(f"Corrupted checkpoint schema: {str(e_pydantic)}")

    # ── Workflow Lifecycle API ──────────────────────────────────────────────────

    async def create_workflow(self, goal: Goal, plan: Optional[ExecutionPlan] = None) -> Dict[str, Any]:
        """Creates a new workflow record and persists initial state."""
        workflow_id = f"wf_{uuid.uuid4().hex[:8]}"

        async with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO workflows (workflow_id, goal_id, status, archived, created_at, updated_at) VALUES (?, ?, ?, 0, ?, ?)",
                    (workflow_id, goal.goal_id, goal.status.value, time.time(), time.time())
                )
                conn.commit()

        log_structured(backend_log, "INFO", f"[WorkflowManager] Created workflow {workflow_id} for Goal {goal.goal_id}.")

        event_bus.emit(
            autonomous_config.EVENT_WORKFLOW_CREATED,
            workflow_id=workflow_id,
            goal_id=goal.goal_id
        )

        return {
            "workflow_id": workflow_id,
            "goal_id": goal.goal_id,
            "status": goal.status.value,
            "archived": False
        }

    async def save_checkpoint(
        self, 
        workflow_id: str, 
        goal: Goal, 
        plan: ExecutionPlan, 
        snapshot: ProgressSnapshot, 
        task_states: Dict[str, ExecutionState], 
        task_results: Optional[Dict[str, TaskResult]] = None, 
        recovery_history: Optional[List[RecoveryAttempt]] = None, 
        execution_context: Optional[Dict[str, Any]] = None
    ) -> FullWorkflowCheckpoint:
        """Saves an immutable execution checkpoint to persistence layer under concurrency lock."""
        async with self._lock:
            # Check workflow exists
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT workflow_id FROM workflows WHERE workflow_id = ?", (workflow_id,))
                row = cursor.fetchone()
                if not row:
                    raise ValueError(f"Unknown workflow_id '{workflow_id}'. Cannot save checkpoint.")

            checkpoint = FullWorkflowCheckpoint(
                workflow_id=workflow_id,
                goal_id=goal.goal_id,
                version=autonomous_config.WORKFLOW_CHECKPOINT_VERSION,
                timestamp=time.time(),
                goal=goal,
                plan=plan,
                progress_snapshot=snapshot,
                task_states=task_states,
                task_results=task_results or {},
                recovery_history=recovery_history or [],
                execution_context=execution_context or {}
            )

            chk_json = checkpoint.model_dump_json()

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO workflow_checkpoints (checkpoint_id, workflow_id, version, checkpoint_data, timestamp) VALUES (?, ?, ?, ?, ?)",
                    (checkpoint.checkpoint_id, workflow_id, checkpoint.version, chk_json, checkpoint.timestamp)
                )
                cursor.execute(
                    "UPDATE workflows SET status = ?, updated_at = ? WHERE workflow_id = ?",
                    (goal.status.value, checkpoint.timestamp, workflow_id)
                )
                conn.commit()

        log_structured(backend_log, "INFO", f"[WorkflowManager] Checkpoint {checkpoint.checkpoint_id} saved for workflow {workflow_id}.")

        event_bus.emit(
            autonomous_config.EVENT_CHECKPOINT_SAVED,
            checkpoint_id=checkpoint.checkpoint_id,
            workflow_id=workflow_id,
            timestamp=checkpoint.timestamp
        )
        event_bus.emit(
            autonomous_config.EVENT_WORKFLOW_CHECKPOINT_CREATED,
            workflow_id=workflow_id,
            checkpoint_id=checkpoint.checkpoint_id,
            completed_nodes=snapshot.completed_tasks
        )

        return checkpoint

    async def load_checkpoint(self, workflow_id: str, checkpoint_id: Optional[str] = None) -> FullWorkflowCheckpoint:
        """Loads and validates a checkpoint from persistence layer."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if checkpoint_id:
                cursor.execute(
                    "SELECT checkpoint_data FROM workflow_checkpoints WHERE workflow_id = ? AND checkpoint_id = ?",
                    (workflow_id, checkpoint_id)
                )
            else:
                cursor.execute(
                    "SELECT checkpoint_data FROM workflow_checkpoints WHERE workflow_id = ? ORDER BY timestamp DESC LIMIT 1",
                    (workflow_id,)
                )
            row = cursor.fetchone()

        if not row:
            raise ValueError(f"No checkpoint found for workflow_id '{workflow_id}'" + (f" (checkpoint_id '{checkpoint_id}')" if checkpoint_id else ""))

        checkpoint = self.validate_checkpoint(row[0])

        event_bus.emit(
            autonomous_config.EVENT_CHECKPOINT_LOADED,
            checkpoint_id=checkpoint.checkpoint_id,
            workflow_id=workflow_id
        )

        return checkpoint

    async def resume_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Restores workflow state from the latest validated checkpoint.
        Does NOT automatically execute tasks (strictly returns restored state payload).
        """
        checkpoint = await self.load_checkpoint(workflow_id)

        log_structured(backend_log, "INFO", f"[WorkflowManager] Restored workflow {workflow_id} state from checkpoint {checkpoint.checkpoint_id}.")

        event_bus.emit(
            autonomous_config.EVENT_WORKFLOW_RESUMED,
            workflow_id=workflow_id,
            checkpoint_id=checkpoint.checkpoint_id
        )

        return {
            "workflow_id": workflow_id,
            "goal": checkpoint.goal,
            "plan": checkpoint.plan,
            "progress_snapshot": checkpoint.progress_snapshot,
            "task_states": checkpoint.task_states,
            "task_results": checkpoint.task_results,
            "recovery_history": checkpoint.recovery_history,
            "execution_context": checkpoint.execution_context
        }

    async def archive_workflow(self, workflow_id: str) -> bool:
        """Flags a workflow as archived."""
        async with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE workflows SET archived = 1, updated_at = ? WHERE workflow_id = ?", (time.time(), workflow_id))
                updated = cursor.rowcount > 0
                conn.commit()

        if updated:
            log_structured(backend_log, "INFO", f"[WorkflowManager] Archived workflow {workflow_id}.")
            event_bus.emit(autonomous_config.EVENT_WORKFLOW_ARCHIVED, workflow_id=workflow_id)

        return updated

    async def delete_workflow(self, workflow_id: str) -> bool:
        """Deletes a workflow and all associated checkpoints from persistence."""
        async with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM workflow_checkpoints WHERE workflow_id = ?", (workflow_id,))
                cursor.execute("DELETE FROM workflows WHERE workflow_id = ?", (workflow_id,))
                deleted = cursor.rowcount > 0
                conn.commit()

        if deleted:
            log_structured(backend_log, "INFO", f"[WorkflowManager] Deleted workflow {workflow_id}.")
            event_bus.emit(autonomous_config.EVENT_WORKFLOW_DELETED, workflow_id=workflow_id)

        return deleted

    async def list_workflows(self, archived: Optional[bool] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Lists workflows with optional archived filtering."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if archived is None:
                cursor.execute("SELECT workflow_id, goal_id, status, archived, created_at, updated_at FROM workflows ORDER BY updated_at DESC LIMIT ?", (limit,))
            else:
                arch_val = 1 if archived else 0
                cursor.execute("SELECT workflow_id, goal_id, status, archived, created_at, updated_at FROM workflows WHERE archived = ? ORDER BY updated_at DESC LIMIT ?", (arch_val, limit))
            rows = cursor.fetchall()

        results = []
        for r in rows:
            results.append({
                "workflow_id": r[0],
                "goal_id": r[1],
                "status": r[2],
                "archived": bool(r[3]),
                "created_at": r[4],
                "updated_at": r[5]
            })
        return results


workflow_manager = WorkflowManager()
