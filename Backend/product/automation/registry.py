"""
JARVIS Product 1.7 - Workflow Registry.
Provides in-memory and SQLite-backed registry for registered active workflows.
"""

import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional
from .models import (
    Workflow,
    WorkflowStatus,
    TriggerConfig,
    ConditionConfig,
    ActionStep,
    WorkflowPermissions,
    RetryPolicyConfig,
    ExecutionStrategy,
)

logger = logging.getLogger(__name__)


class WorkflowRegistry:
    def __init__(self, db_path: str = "logs/jarvis_automation.db"):
        self.db_path = db_path
        self._memory_workflows: Dict[str, Workflow] = {}

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        conn = self._get_connection()
        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS automation_workflows (
                        workflow_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT NOT NULL,
                        owner TEXT NOT NULL,
                        version INTEGER DEFAULT 1,
                        trigger_json TEXT NOT NULL,
                        conditions_json TEXT,
                        actions_json TEXT NOT NULL,
                        execution_strategy TEXT NOT NULL,
                        permissions_json TEXT,
                        timeout_seconds REAL DEFAULT 300.0,
                        retry_policy_json TEXT,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        tags_json TEXT
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_wf_owner ON automation_workflows(owner);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_wf_status ON automation_workflows(status);")
        finally:
            conn.close()

    def register_workflow(self, workflow: Workflow) -> bool:
        self._memory_workflows[workflow.workflow_id] = workflow
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO automation_workflows (
                        workflow_id, name, description, owner, version, trigger_json,
                        conditions_json, actions_json, execution_strategy, permissions_json,
                        timeout_seconds, retry_policy_json, status, created_at, updated_at, tags_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        workflow.workflow_id,
                        workflow.name,
                        workflow.description,
                        workflow.owner,
                        workflow.version,
                        json.dumps(workflow.trigger.to_dict()),
                        json.dumps([c.to_dict() for c in workflow.conditions]),
                        json.dumps([a.to_dict() for a in workflow.actions]),
                        workflow.execution_strategy.value,
                        json.dumps(workflow.permissions.to_dict()),
                        workflow.timeout_seconds,
                        json.dumps(workflow.retry_policy.to_dict()),
                        workflow.status.value,
                        workflow.created_at.isoformat(),
                        workflow.updated_at.isoformat(),
                        json.dumps(workflow.tags),
                    ),
                )
            return True
        except Exception as e:
            logger.error(f"register_workflow error: {e}")
            return False
        finally:
            conn.close()

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        if workflow_id in self._memory_workflows:
            return self._memory_workflows[workflow_id]

        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT * FROM automation_workflows WHERE workflow_id = ?", (workflow_id,))
            row = cursor.fetchone()
            if not row:
                return None

            wf = self._row_to_workflow(row)
            self._memory_workflows[wf.workflow_id] = wf
            return wf
        finally:
            conn.close()

    def list_workflows(self, owner_id: Optional[str] = None, status: Optional[WorkflowStatus] = None) -> List[Workflow]:
        conn = self._get_connection()
        try:
            query = "SELECT * FROM automation_workflows WHERE 1=1"
            params = []
            if owner_id:
                query += " AND owner = ?"
                params.append(owner_id)
            if status:
                query += " AND status = ?"
                params.append(status.value)
            query += " ORDER BY created_at DESC"

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_workflow(r) for r in rows]
        finally:
            conn.close()

    def delete_workflow(self, workflow_id: str) -> bool:
        if workflow_id in self._memory_workflows:
            del self._memory_workflows[workflow_id]
        conn = self._get_connection()
        try:
            with conn:
                conn.execute("DELETE FROM automation_workflows WHERE workflow_id = ?", (workflow_id,))
            return True
        except Exception as e:
            logger.error(f"delete_workflow error: {e}")
            return False
        finally:
            conn.close()

    def _row_to_workflow(self, row: sqlite3.Row) -> Workflow:
        from datetime import datetime
        trig_dict = json.loads(row["trigger_json"]) if row["trigger_json"] else {}
        cond_list = json.loads(row["conditions_json"]) if row["conditions_json"] else []
        act_list = json.loads(row["actions_json"]) if row["actions_json"] else []
        perm_dict = json.loads(row["permissions_json"]) if row["permissions_json"] else {}
        retry_dict = json.loads(row["retry_policy_json"]) if row["retry_policy_json"] else {}
        tags_list = json.loads(row["tags_json"]) if row["tags_json"] else []

        return Workflow(
            workflow_id=row["workflow_id"],
            name=row["name"],
            description=row["description"],
            owner=row["owner"],
            version=row["version"],
            trigger=TriggerConfig.from_dict(trig_dict),
            conditions=[ConditionConfig.from_dict(c) for c in cond_list],
            actions=[ActionStep.from_dict(a) for a in act_list],
            execution_strategy=ExecutionStrategy(row["execution_strategy"]),
            permissions=WorkflowPermissions.from_dict(perm_dict),
            timeout_seconds=row["timeout_seconds"],
            retry_policy=RetryPolicyConfig.from_dict(retry_dict),
            status=WorkflowStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            tags=tags_list,
        )
