"""
JARVIS Product 1.7 - Event Bus Watcher Trigger.
Subscribes to EventBus topics (Knowledge ingestion, tool execution, plugin events) to trigger workflows.
"""

import logging
from typing import Dict, Any, List
from .base import BaseTriggerListener
from ..models import Workflow, TriggerType

logger = logging.getLogger(__name__)


class EventWatcher(BaseTriggerListener):
    def __init__(self):
        super().__init__("EventWatcher")
        self._subscribed_workflows: Dict[str, List[Workflow]] = {}
        self._running = False

    def register_event_workflow(self, workflow: Workflow) -> None:
        topic = workflow.trigger.event_topic or "global"
        if topic not in self._subscribed_workflows:
            self._subscribed_workflows[topic] = []
        self._subscribed_workflows[topic].append(workflow)

    def start(self) -> None:
        self._running = True
        logger.info("EventWatcher listener started.")

    def stop(self) -> None:
        self._running = False
        logger.info("EventWatcher listener stopped.")

    def on_event_emitted(self, topic: str, payload: Dict[str, Any]) -> None:
        if not self._running or not self.callback:
            return

        workflows = self._subscribed_workflows.get(topic, [])
        for wf in workflows:
            context = {"event_topic": topic, "payload": payload}
            try:
                self.callback(wf, context)
            except Exception as e:
                logger.error(f"EventWatcher callback error for workflow {wf.workflow_id}: {e}")
