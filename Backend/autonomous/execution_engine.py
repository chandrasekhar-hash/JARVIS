import time
import asyncio
from typing import Dict, Any, Optional, Set
from brain.event_bus import event_bus
from tools.registry import registry
from tools.telemetry import log_structured, backend_log
from autonomous.models import Task, TaskResult, ExecutionState
from autonomous.interfaces import IExecutionEngine
from autonomous.config import autonomous_config


class ExecutionEngine(IExecutionEngine):
    """Subsystem responsible for executing task steps via ToolRegistry and managing execution states."""

    def __init__(self):
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._cancelled_tasks: Set[str] = set()

    async def execute_task(self, task: Task, selected_tool: Dict[str, Any]) -> TaskResult:
        """
        Executes a single ready Task using the specified selected_tool parameters.
        Tracks state transitions and emits EventBus domain events.
        """
        task_id = task.task_id
        tool_name = selected_tool.get("selected_tool", "agent_reasoning")
        args = selected_tool.get("arguments", {})
        is_valid = selected_tool.get("is_valid", True)

        # 1. Check for pre-execution cancellation
        if task_id in self._cancelled_tasks:
            log_structured(backend_log, "INFO", f"[ExecutionEngine] Task {task_id} was cancelled before start.")
            event_bus.emit(autonomous_config.EVENT_EXECUTION_CANCELLED, task_id=task_id, reason="Cancelled prior to start")
            return TaskResult(
                task_id=task_id,
                status=ExecutionState.CANCELLED,
                error="Task cancelled before execution.",
                execution_time_seconds=0.0
            )

        # 2. Check for invalid tool selection
        if not is_valid:
            reason = selected_tool.get("reason", "Invalid tool selection")
            log_structured(backend_log, "WARNING", f"[ExecutionEngine] Task {task_id} tool validation failed: {reason}")
            event_bus.emit(
                autonomous_config.EVENT_TASK_FAILED,
                task_id=task_id,
                error=reason,
                retry_count=0
            )
            return TaskResult(
                task_id=task_id,
                status=ExecutionState.FAILED,
                error=f"Tool selection invalid: {reason}",
                execution_time_seconds=0.0
            )

        # 3. Emit TaskStarted & ExecutionStarted events
        start_time = time.time()
        log_structured(
            backend_log, 
            "INFO", 
            f"[ExecutionEngine] Starting execution for Task {task_id} using '{tool_name}'"
        )

        event_bus.emit(
            autonomous_config.EVENT_TASK_STARTED,
            task_id=task_id,
            tool_name=tool_name,
            started_at=start_time
        )
        event_bus.emit(
            autonomous_config.EVENT_EXECUTION_STARTED,
            task_id=task_id,
            started_at=start_time
        )

        # 4. Dispatch Async Tool Execution with Timeout
        timeout = task.timeout_seconds or autonomous_config.DEFAULT_TASK_TIMEOUT_SECONDS
        current_async_task = asyncio.current_task()
        if current_async_task:
            self._active_tasks[task_id] = current_async_task

        try:
            if tool_name in registry.tools:
                output = await asyncio.wait_for(
                    registry.execute(tool_name, **args),
                    timeout=timeout
                )
            else:
                # Simulating fallback/agent reasoning execution step
                await asyncio.sleep(0.05)
                output = f"Execution step '{task.name}' completed via {tool_name}."

            elapsed = time.time() - start_time

            # Check if task was cancelled during execution
            if task_id in self._cancelled_tasks:
                event_bus.emit(autonomous_config.EVENT_EXECUTION_CANCELLED, task_id=task_id)
                return TaskResult(
                    task_id=task_id,
                    status=ExecutionState.CANCELLED,
                    error="Task cancelled during execution.",
                    execution_time_seconds=elapsed
                )

            log_structured(
                backend_log, 
                "INFO", 
                f"[ExecutionEngine] Task {task_id} completed successfully in {elapsed:.3f}s"
            )

            event_bus.emit(
                autonomous_config.EVENT_TASK_COMPLETED,
                task_id=task_id,
                output=output,
                execution_time=elapsed
            )
            event_bus.emit(
                autonomous_config.EVENT_EXECUTION_COMPLETED,
                task_id=task_id,
                execution_time=elapsed
            )

            return TaskResult(
                task_id=task_id,
                status=ExecutionState.COMPLETED,
                output=output,
                execution_time_seconds=elapsed
            )

        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            err_msg = f"Task execution timed out after {timeout}s"
            log_structured(backend_log, "WARNING", f"[ExecutionEngine] Task {task_id} timeout: {err_msg}")

            event_bus.emit(
                autonomous_config.EVENT_TASK_FAILED,
                task_id=task_id,
                error=err_msg,
                retry_count=0
            )
            return TaskResult(
                task_id=task_id,
                status=ExecutionState.FAILED,
                error=err_msg,
                execution_time_seconds=elapsed
            )

        except Exception as e:
            elapsed = time.time() - start_time
            err_msg = str(e)
            log_structured(backend_log, "ERROR", f"[ExecutionEngine] Task {task_id} error: {err_msg}")

            event_bus.emit(
                autonomous_config.EVENT_TASK_FAILED,
                task_id=task_id,
                error=err_msg,
                retry_count=0
            )
            return TaskResult(
                task_id=task_id,
                status=ExecutionState.FAILED,
                error=err_msg,
                execution_time_seconds=elapsed
            )

        finally:
            self._active_tasks.pop(task_id, None)

    async def cancel_task(self, task_id: str) -> bool:
        """Flags a task as cancelled and cancels running coroutine if active."""
        self._cancelled_tasks.add(task_id)
        if task_id in self._active_tasks:
            async_task = self._active_tasks.get(task_id)
            if async_task and not async_task.done():
                async_task.cancel()
        log_structured(backend_log, "INFO", f"[ExecutionEngine] Task {task_id} cancelled.")
        return True


execution_engine = ExecutionEngine()
