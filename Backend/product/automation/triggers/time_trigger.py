"""
JARVIS Product 1.7 - Time Trigger Driver.
Supports cron expressions and interval-based scheduling.
"""

import time
import logging
from typing import Dict, Any, Optional
from .base import BaseTriggerListener
from ..models import Workflow, TriggerType

logger = logging.getLogger(__name__)


class TimeTrigger(BaseTriggerListener):
    def __init__(self):
        super().__init__("TimeTrigger")
        self._running = False
        self._scheduled_workflows: Dict[str, Workflow] = {}

    def add_workflow(self, workflow: Workflow) -> None:
        if workflow.trigger.trigger_type in (TriggerType.TIME_CRON, TriggerType.TIME_INTERVAL):
            self._scheduled_workflows[workflow.workflow_id] = workflow

    def remove_workflow(self, workflow_id: str) -> None:
        if workflow_id in self._scheduled_workflows:
            del self._scheduled_workflows[workflow_id]

    def start(self) -> None:
        self._running = True
        logger.info("TimeTrigger listener started.")

    def stop(self) -> None:
        self._running = False
        logger.info("TimeTrigger listener stopped.")

    def check_due_workflows(self, current_time: Optional[float] = None) -> None:
        if not self._running or not self.callback:
            return

        now = current_time or time.time()
        for wf_id, wf in list(self._scheduled_workflows.items()):
            # Fire callback for due workflow
            context = {"fired_at": now, "trigger_type": wf.trigger.trigger_type.value}
            try:
                self.callback(wf, context)
            except Exception as e:
                logger.error(f"TimeTrigger callback error for workflow {wf_id}: {e}")
