import uuid
import time
import asyncio
from typing import Dict, List, Optional, Callable
from brain.models import TaskMetadata
from brain.event_bus import event_bus
from tools.telemetry import log_structured, backend_log

class TaskManager:
    def __init__(self):
        self._tasks: Dict[str, TaskMetadata] = {}
        self._async_tasks: Dict[str, asyncio.Task] = {}
        self._callables: Dict[str, Callable] = {}

    def create_task(self, task_func: Callable, description: str, *args, **kwargs) -> TaskMetadata:
        """Creates and launches an asynchronous background task."""
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        meta = TaskMetadata(
            task_id=task_id,
            description=description,
            started_time=time.time()
        )
        self._tasks[task_id] = meta
        self._callables[task_id] = (task_func, args, kwargs)

        log_structured(backend_log, "INFO", f"[TaskManager] Created task {task_id}: '{description}'")
        event_bus.emit("TaskStarted", task_id=task_id, description=description)

        async_task = asyncio.create_task(self._run_task_wrapper(task_id, task_func, *args, **kwargs))
        self._async_tasks[task_id] = async_task

        return meta

    async def _run_task_wrapper(self, task_id: str, task_func: Callable, *args, **kwargs):
        meta = self._tasks[task_id]
        meta.status = "running"
        meta.progress = 10.0
        meta.current_step = "Executing tool sequence"
        event_bus.emit("TaskProgress", task_id=task_id, progress=10.0, step=meta.current_step)

        try:
            if asyncio.iscoroutinefunction(task_func):
                res = await task_func(*args, **kwargs)
            else:
                res = task_func(*args, **kwargs)

            meta.status = "completed"
            meta.progress = 100.0
            meta.current_step = "Finished successfully"
            meta.finished_time = time.time()
            log_structured(backend_log, "INFO", f"[TaskManager] Task {task_id} completed successfully")
            event_bus.emit("TaskCompleted", task_id=task_id, result=str(res))
            return res
        except asyncio.CancelledError:
            meta.status = "cancelled"
            meta.finished_time = time.time()
            meta.current_step = "Task cancelled by user"
            log_structured(backend_log, "WARNING", f"[TaskManager] Task {task_id} cancelled")
            event_bus.emit("TaskFailed", task_id=task_id, error="Task cancelled")
            raise
        except Exception as e:
            meta.status = "failed"
            meta.finished_time = time.time()
            meta.error = str(e)
            meta.current_step = f"Failed: {str(e)}"
            log_structured(backend_log, "ERROR", f"[TaskManager] Task {task_id} failed: {str(e)}")
            event_bus.emit("TaskFailed", task_id=task_id, error=str(e))

    def get_task_status(self, task_id: str) -> Optional[TaskMetadata]:
        """Retrieves metadata status for a given task ID."""
        return self._tasks.get(task_id)

    def list_tasks(self) -> List[TaskMetadata]:
        """Returns a list of all tracked background tasks."""
        return list(self._tasks.values())

    def cancel_task(self, task_id: str) -> bool:
        """Cancels a running background task."""
        if task_id in self._async_tasks:
            async_task = self._async_tasks[task_id]
            if not async_task.done():
                async_task.cancel()
                meta = self._tasks.get(task_id)
                if meta:
                    meta.status = "cancelled"
                    meta.finished_time = time.time()
                return True
        return False

    def retry_task(self, task_id: str) -> Optional[TaskMetadata]:
        """Retries a failed or cancelled task."""
        if task_id in self._callables:
            task_func, args, kwargs = self._callables[task_id]
            meta = self._tasks[task_id]
            log_structured(backend_log, "INFO", f"[TaskManager] Retrying task {task_id}")
            meta.status = "pending"
            meta.error = None
            meta.started_time = time.time()
            meta.finished_time = None

            async_task = asyncio.create_task(self._run_task_wrapper(task_id, task_func, *args, **kwargs))
            self._async_tasks[task_id] = async_task
            return meta
        return None

task_manager = TaskManager()
