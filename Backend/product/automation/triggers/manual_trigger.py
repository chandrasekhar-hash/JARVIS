"""
JARVIS Product 1.7 - Manual Trigger Driver.
Supports on-demand manual workflow triggers via API or tool calling.
"""

import logging
from typing import Dict, Any
from .base import BaseTriggerListener
from ..models import Workflow

logger = logging.getLogger(__name__)


class ManualTrigger(BaseTriggerListener):
    def __init__(self):
        super().__init__("ManualTrigger")
        self._running = False

    def start(self) -> None:
        self._running = True
        logger.info("ManualTrigger listener started.")

    def stop(self) -> None:
        self._running = False
        logger.info("ManualTrigger listener stopped.")

    def trigger_manually(self, workflow: Workflow, user_params: Dict[str, Any] = None) -> None:
        if not self._running or not self.callback:
            return

        context = {"triggered_by": "manual", "user_params": user_params or {}}
        self.callback(workflow, context)
