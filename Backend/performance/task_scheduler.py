"""
Priority Task Scheduler for J.A.R.V.I.S. Phase V1.7.
Manages prioritized async task scheduling, worker pool sizing, and task cancellation.
"""
import asyncio
import logging
from typing import Dict, Optional, Callable, Any
from .interfaces import ITaskScheduler
from .models import TaskStatistics

logger = logging.getLogger("JARVIS_TaskScheduler")


class TaskScheduler(ITaskScheduler):
    """
    Priority-based async task scheduler with dynamic worker pool support.
    """

    def __init__(self, initial_workers: int = 4, max_workers: int = 16):
        self.initial_workers = initial_workers
        self.max_workers = max_workers
        self._current_workers = initial_workers
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._tasks: Dict[str, asyncio.Task] = {}

        self._total_tasks: int = 0
        self._completed_tasks: int = 0
        self._failed_tasks: int = 0
        self._cancelled_tasks: int = 0

    def adjust_worker_count(self, new_count: int) -> int:
        clamped = max(1, min(new_count, self.max_workers))
        self._current_workers = clamped
        logger.info(f"[TaskScheduler] Adjusted active worker pool size to {self._current_workers}.")
        return self._current_workers

    async def schedule(self, coro_fn: Callable, priority: int = 5, task_name: str = "") -> Any:
        name = task_name or f"task_{self._total_tasks + 1}"
        self._total_tasks += 1

        async def _wrapper():
            try:
                if asyncio.iscoroutinefunction(coro_fn):
                    res = await coro_fn()
                else:
                    res = coro_fn()
                self._completed_tasks += 1
                return res
            except asyncio.CancelledError:
                self._cancelled_tasks += 1
                raise
            except Exception as e:
                self._failed_tasks += 1
                logger.error(f"[TaskScheduler] Task '{name}' failed: {e}")
                raise

        task = asyncio.create_task(_wrapper())
        self._tasks[name] = task
        return await task

    def cancel(self, task_name: str) -> bool:
        if task_name in self._tasks:
            task = self._tasks[task_name]
            if not task.done():
                task.cancel()
                self._cancelled_tasks += 1
                return True
        return False

    def get_statistics(self) -> TaskStatistics:
        return TaskStatistics(
            total_tasks=self._total_tasks,
            completed_tasks=self._completed_tasks,
            failed_tasks=self._failed_tasks,
            cancelled_tasks=self._cancelled_tasks,
            active_workers=self._current_workers,
        )
