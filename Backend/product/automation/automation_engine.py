"""
JARVIS Product 1.7 - Master Automation Engine Entrypoint.
Initializes WorkflowManager, Scheduler, TaskQueue worker, ExecutionHistoryStore, and Tool Action Executors.
"""

import os
import time
import threading
import logging
from typing import List, Dict, Any, Optional
from .models import Workflow, WorkflowRunRecord, TriggerConfig, ActionStep, ConditionConfig, WorkflowStatus
from .workflow_manager import WorkflowManager
from .registry import WorkflowRegistry
from .scheduler import AutomationScheduler
from .queue import TaskQueue
from .executor import ActionExecutor
from .storage import SQLiteExecutionHistoryStore
from .notifications import notification_interface
from .telemetry import automation_telemetry
from .logging import automation_logger

logger = logging.getLogger(__name__)


class AutomationManager:
    def __init__(self, db_path: str = "logs/jarvis_automation.db"):
        self.db_path = db_path

        # 1. Storage & Registry
        self.registry = WorkflowRegistry(db_path=db_path)
        self.history_store = SQLiteExecutionHistoryStore(db_path=db_path)

        # 2. Workflow Governance & Queue
        self.workflow_manager = WorkflowManager(registry=self.registry)
        self.task_queue = TaskQueue()

        # 3. Scheduler & Action Executor
        self.scheduler = AutomationScheduler(task_queue=self.task_queue)
        self.action_executor = ActionExecutor()

        # Worker thread
        self._worker_thread: Optional[threading.Thread] = None
        self._worker_running = False
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return

        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        self.registry.initialize()
        self.history_store.initialize()
        self.scheduler.start()

        # Register tools with P1.5 Tool Engine
        try:
            from ..knowledge.tools import get_knowledge_tool_metadatas
            from .tools import get_automation_tool_metadatas
            from ..tools import tool_execution_manager_instance
            for meta in get_knowledge_tool_metadatas() + get_automation_tool_metadatas():
                tool_execution_manager_instance.metadata_registry.register_tool_metadata(meta)
        except Exception as e:
            logger.warning(f"Tool registration notice: {e}")

        # Start Async Worker Thread
        self._worker_running = True
        self._worker_thread = threading.Thread(target=self._run_worker_loop, daemon=True)
        self._worker_thread.start()

        self._initialized = True
        logger.info("JARVIS Automation Engine Product 1.7 initialized successfully.")

    def _run_worker_loop(self) -> None:
        while self._worker_running:
            item = self.task_queue.pop_task()
            if not item:
                time.sleep(0.1)
                continue

            workflow, run_record, trigger_context = item
            start_time = time.time()

            try:
                # Save initial run record
                self.history_store.save_run_record(run_record)

                # Execute Workflow Actions via P1.5 Tool Execution Engine
                success = self.action_executor.execute_workflow_actions(workflow, run_record)

                duration = (time.time() - start_time) * 1000.0
                self.history_store.save_run_record(run_record)

                automation_telemetry.record_execution(success, duration)
                automation_logger.log_event(
                    event_name="WORKFLOW_RUN_FINISHED",
                    user_id=workflow.owner,
                    workflow_id=workflow.workflow_id,
                    run_id=run_record.run_id,
                    details={"status": run_record.status.value, "steps_completed": run_record.steps_completed},
                    duration_ms=duration,
                )

                if not success:
                    notification_interface.dispatch(
                        title=f"Workflow '{workflow.name}' Failed",
                        message=f"Run {run_record.run_id} failed: {run_record.error_details}",
                        level="warning",
                    )
                    self.task_queue.push_to_dlq(workflow, run_record, run_record.error_details or "Action failure")

            except Exception as e:
                logger.error(f"Worker exception executing workflow {workflow.workflow_id}: {e}")
                run_record.error_details = str(e)
                self.history_store.save_run_record(run_record)

    def shutdown(self) -> None:
        self._worker_running = False
        self.scheduler.stop()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
        logger.info("JARVIS Automation Engine shut down cleanly.")

    # High-level Public API Methods
    def create_workflow(
        self,
        name: str,
        description: str,
        owner: str,
        trigger: TriggerConfig,
        actions: List[ActionStep],
        conditions: Optional[List[ConditionConfig]] = None,
        tags: Optional[List[str]] = None,
    ) -> Workflow:
        self.initialize()
        wf = self.workflow_manager.create_workflow(
            name=name,
            description=description,
            owner=owner,
            trigger=trigger,
            actions=actions,
            conditions=conditions,
            tags=tags,
        )
        self.scheduler.schedule_workflow(wf)
        return wf

    def trigger_workflow_manually(self, workflow_id: str, user_params: Dict[str, Any] = None) -> str:
        self.initialize()
        wf = self.workflow_manager.get_workflow(workflow_id)
        if not wf:
            raise ValueError(f"Workflow '{workflow_id}' not found.")
        return self.scheduler.trigger_manually(wf, user_params)

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        self.initialize()
        return self.workflow_manager.get_workflow(workflow_id)

    def list_workflows(self, owner_id: Optional[str] = None) -> List[Workflow]:
        self.initialize()
        return self.workflow_manager.list_workflows(owner_id=owner_id)

    def pause_workflow(self, workflow_id: str, user_id: str) -> bool:
        self.initialize()
        self.scheduler.unschedule_workflow(workflow_id)
        return self.workflow_manager.pause_workflow(workflow_id, user_id)

    def resume_workflow(self, workflow_id: str, user_id: str) -> bool:
        self.initialize()
        success = self.workflow_manager.resume_workflow(workflow_id, user_id)
        if success:
            wf = self.workflow_manager.get_workflow(workflow_id)
            if wf:
                self.scheduler.schedule_workflow(wf)
        return success

    def delete_workflow(self, workflow_id: str, user_id: str) -> bool:
        self.initialize()
        self.scheduler.unschedule_workflow(workflow_id)
        return self.workflow_manager.delete_workflow(workflow_id, user_id)

    def list_execution_history(
        self,
        workflow_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[WorkflowRunRecord]:
        self.initialize()
        return self.history_store.list_run_records(workflow_id=workflow_id, owner_id=owner_id, limit=limit)

    def get_telemetry_metrics(self) -> Dict[str, Any]:
        return automation_telemetry.get_metrics()


automation_manager_instance = AutomationManager()
