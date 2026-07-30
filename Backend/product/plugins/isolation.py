"""
Product 1.4 Plugin Error Isolation Guard & Circuit Breaker.
"""
import asyncio
import inspect
import logging
import time
from typing import Any, Callable, Dict, Optional, Tuple
from .models import PluginState, PluginStatus

logger = logging.getLogger("JARVIS_PluginIsolationGuard")


class PluginExecutionTimeoutException(Exception):
    """Exception raised when a plugin execution exceeds max time budget."""
    pass


class PluginIsolationGuard:
    """
    Fault isolation wrapper protecting JARVIS core execution loop against
    plugin crashes, infinite loops, exceptions, and resource spikes.
    """

    MAX_CONSECUTIVE_FAILURES = 5
    DEFAULT_TIMEOUT_SECONDS = 10.0

    @staticmethod
    async def execute_async(
        state: PluginState,
        handler: Callable[..., Any],
        *args: Any,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        **kwargs: Any,
    ) -> Tuple[bool, Any, Optional[str]]:
        """
        Executes an async or sync handler safely within isolation boundaries and timeout limits.
        Returns:
            (success, result, error_message)
        """
        if state.status in (PluginStatus.DISABLED, PluginStatus.FAILED, PluginStatus.UNLOADED):
            return False, None, f"Cannot execute skill: Plugin '{state.plugin_id}' is in '{state.status.value}' state."

        try:
            state.status = PluginStatus.EXECUTING

            if inspect.iscoroutinefunction(handler):
                coro = handler(*args, **kwargs)
                result = await asyncio.wait_for(coro, timeout=timeout_seconds)
            else:
                # Run synchronous function in asyncio executor to prevent loop blocking
                loop = asyncio.get_running_loop()
                func_call = lambda: handler(*args, **kwargs)
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, func_call),
                    timeout=timeout_seconds,
                )

            # Execution succeeded -> Reset failure counters
            state.status = PluginStatus.ACTIVATED
            state.consecutive_failures = 0
            state.health_ok = True
            state.error_message = None
            return True, result, None

        except asyncio.TimeoutError:
            err_msg = f"Plugin '{state.plugin_id}' execution timed out (> {timeout_seconds}s)."
            logger.error(f"[IsolationGuard] TIMEOUT: {err_msg}")
            PluginIsolationGuard._record_failure(state, err_msg)
            return False, None, err_msg

        except Exception as e:
            err_msg = f"Unhandled exception during plugin '{state.plugin_id}' execution: {str(e)}"
            logger.error(f"[IsolationGuard] ERROR: {err_msg}", exc_info=True)
            PluginIsolationGuard._record_failure(state, err_msg)
            return False, None, err_msg

    @staticmethod
    def execute_sync(
        state: PluginState,
        handler: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Tuple[bool, Any, Optional[str]]:
        """
        Synchronous error isolation wrapper for lifecycle hooks (on_initialize, on_activate, etc.).
        """
        try:
            result = handler(*args, **kwargs)
            state.consecutive_failures = 0
            state.health_ok = True
            return True, result, None
        except Exception as e:
            err_msg = f"Exception in plugin '{state.plugin_id}' synchronous handler: {str(e)}"
            logger.error(f"[IsolationGuard] {err_msg}", exc_info=True)
            PluginIsolationGuard._record_failure(state, err_msg)
            return False, None, err_msg

    @staticmethod
    def _record_failure(state: PluginState, error_message: str) -> None:
        """Increments failure count and triggers Circuit Breaker if threshold reached."""
        state.consecutive_failures += 1
        state.error_message = error_message

        if state.consecutive_failures >= PluginIsolationGuard.MAX_CONSECUTIVE_FAILURES:
            state.status = PluginStatus.FAILED
            state.health_ok = False
            logger.critical(
                f"[IsolationGuard] CIRCUIT BREAKER TRIGGERED: Plugin '{state.plugin_id}' "
                f"exceeded max consecutive failures ({PluginIsolationGuard.MAX_CONSECUTIVE_FAILURES}). "
                f"Transitioned plugin to FAILED state to protect core runner."
            )
        else:
            state.status = PluginStatus.ACTIVATED
