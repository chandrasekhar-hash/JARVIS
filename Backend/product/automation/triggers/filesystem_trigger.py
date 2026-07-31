"""
JARVIS Product 1.7 - Filesystem Watcher Trigger.
Monitors directory paths for file creation or drop events.
"""

import os
import logging
from typing import Dict, Any, List
from .base import BaseTriggerListener
from ..models import Workflow

logger = logging.getLogger(__name__)


class FilesystemWatcher(BaseTriggerListener):
    def __init__(self):
        super().__init__("FilesystemWatcher")
        self._watchers: Dict[str, List[Workflow]] = {}
        self._running = False

    def register_folder_watcher(self, workflow: Workflow) -> None:
        directory = workflow.trigger.watch_directory
        if directory:
            if directory not in self._watchers:
                self._watchers[directory] = []
            self._watchers[directory].append(workflow)

    def start(self) -> None:
        self._running = True
        logger.info("FilesystemWatcher listener started.")

    def stop(self) -> None:
        self._running = False
        logger.info("FilesystemWatcher listener stopped.")

    def notify_file_event(self, directory: str, file_path: str, event_type: str = "created") -> None:
        if not self._running or not self.callback:
            return

        workflows = self._watchers.get(directory, [])
        for wf in workflows:
            context = {"file_path": file_path, "event_type": event_type, "directory": directory}
            try:
                self.callback(wf, context)
            except Exception as e:
                logger.error(f"FilesystemWatcher callback error for workflow {wf.workflow_id}: {e}")
