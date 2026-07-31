"""
JARVIS Product 1.7 - Automation Scheduler.
Background scheduling engine evaluating cron/interval tasks and trigger events.
"""

import time
import logging
from typing import Dict, Any, Optional
from .interfaces import IScheduler
from .models import Workflow, WorkflowStatus, TriggerType
from .triggers import TimeTrigger, EventWatcher, FilesystemWatcher, ManualTrigger
from .conditions import ConditionEvaluator
from .queue import TaskQueue

logger = logging.getLogger(__name__)


class AutomationScheduler(IScheduler):
    def __init__(self, task_queue: TaskQueue, condition_evaluator: Optional[ConditionEvaluator] = None):
        self.task_queue = task_queue
        self.condition_evaluator = condition_evaluator or ConditionEvaluator()

        # Trigger listeners
        self.time_trigger = TimeTrigger()
        self.event_watcher = EventWatcher()
        self.filesystem_watcher = FilesystemWatcher()
        self.manual_trigger = ManualTrigger()

        self._running = False
        self._setup_callbacks()

    def _setup_callbacks(self) -> None:
        def trigger_callback(workflow: Workflow, trigger_context: Dict[str, Any]) -> None:
            if workflow.status != WorkflowStatus.ACTIVE:
                return

            # Evaluate preconditions
            all_conditions_passed = True
            for cond in workflow.conditions:
                if not self.condition_evaluator.evaluate(cond, trigger_context):
                    all_conditions_passed = False
                    logger.info(f"Workflow {workflow.workflow_id} skipped: condition '{cond.condition_type}' failed.")
                    break

            if all_conditions_passed:
                run_id = self.task_queue.push_task(workflow, trigger_context)
                logger.info(f"Workflow {workflow.workflow_id} triggered successfully. Run ID: {run_id}")

        self.time_trigger.set_callback(trigger_callback)
        self.event_watcher.set_callback(trigger_callback)
        self.filesystem_watcher.set_callback(trigger_callback)
        self.manual_trigger.set_callback(trigger_callback)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self.time_trigger.start()
        self.event_watcher.start()
        self.filesystem_watcher.start()
        self.manual_trigger.start()
        logger.info("AutomationScheduler background engine started.")

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        self.time_trigger.stop()
        self.event_watcher.stop()
        self.filesystem_watcher.stop()
        self.manual_trigger.stop()
        logger.info("AutomationScheduler background engine stopped.")

    def schedule_workflow(self, workflow: Workflow) -> bool:
        if workflow.trigger.trigger_type in (TriggerType.TIME_CRON, TriggerType.TIME_INTERVAL):
            self.time_trigger.add_workflow(workflow)
        elif workflow.trigger.trigger_type in (TriggerType.KNOWLEDGE_EVENT, TriggerType.PLUGIN_EVENT, TriggerType.TOOL_EVENT):
            self.event_watcher.register_event_workflow(workflow)
        elif workflow.trigger.trigger_type == TriggerType.FILESYSTEM:
            self.filesystem_watcher.register_folder_watcher(workflow)
        return True

    def unschedule_workflow(self, workflow_id: str) -> bool:
        self.time_trigger.remove_workflow(workflow_id)
        return True

    def trigger_manually(self, workflow: Workflow, user_params: Dict[str, Any] = None) -> str:
        run_id = self.task_queue.push_task(workflow, {"triggered_by": "manual", "user_params": user_params or {}})
        return run_id
