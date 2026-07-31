"""
JARVIS Product 1.7 - Task Queue & Dead-Letter Queue.
Async queue decoupling workflow trigger signals from background action execution workers.
"""

import queue
import logging
from typing import Optional, Tuple, Dict, Any, List
from .interfaces import ITaskQueue
from .models import Workflow, WorkflowRunRecord, TriggerType

logger = logging.getLogger(__name__)


class TaskQueue(ITaskQueue):
    def __init__(self, maxsize: int = 1000):
        self._queue: queue.Queue = queue.Queue(maxsize=maxsize)
        self._dead_letter_queue: List[Tuple[Workflow, WorkflowRunRecord, str]] = []

    def push_task(self, workflow: Workflow, trigger_context: Dict[str, Any]) -> str:
        run_record = WorkflowRunRecord.create_new(
            workflow_id=workflow.workflow_id,
            workflow_name=workflow.name,
            owner=workflow.owner,
            trigger_type=workflow.trigger.trigger_type,
            total_steps=len(workflow.actions),
        )
        item = (workflow, run_record, trigger_context)
        self._queue.put(item)
        return run_record.run_id

    def pop_task(self) -> Optional[Tuple[Workflow, WorkflowRunRecord, Dict[str, Any]]]:
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    def push_to_dlq(self, workflow: Workflow, run_record: WorkflowRunRecord, failure_reason: str) -> None:
        logger.warning(f"Workflow {workflow.workflow_id} (Run {run_record.run_id}) pushed to Dead Letter Queue: {failure_reason}")
        self._dead_letter_queue.append((workflow, run_record, failure_reason))

    def get_dlq_items(self) -> List[Tuple[Workflow, WorkflowRunRecord, str]]:
        return self._dead_letter_queue

    def qsize(self) -> int:
        return self._queue.qsize()
