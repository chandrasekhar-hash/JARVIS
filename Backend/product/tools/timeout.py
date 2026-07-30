"""
Product 1.5 Timeout Watchdog & Cancellation Manager.
"""
import asyncio
import logging
from typing import Any, Callable, Tuple, Optional

logger = logging.getLogger("JARVIS_TimeoutManager")


class TimeoutManager:
    """
    Manages non-blocking execution watchdogs and asyncio task cancellation.
    """

    @staticmethod
    async def execute_with_timeout(
        coro_or_func: Any,
        timeout_seconds: float,
        tool_id: str,
    ) -> Tuple[bool, Any, Optional[str], Optional[Exception]]:
        """
        Executes a coroutine with non-blocking watchdog timeout guard.
        Returns:
            (success, result, error_message, exception_object)
        """
        try:
            result = await asyncio.wait_for(coro_or_func, timeout=timeout_seconds)
            return True, result, None, None
        except asyncio.TimeoutError as exc:
            err = f"Tool '{tool_id}' execution timed out (> {timeout_seconds}s)."
            logger.error(f"[TimeoutManager] TIMEOUT: {err}")
            return False, None, err, exc
        except asyncio.CancelledError as exc:
            err = f"Tool '{tool_id}' execution was cancelled by caller."
            logger.warning(f"[TimeoutManager] CANCELLED: {err}")
            return False, None, err, exc
        except Exception as exc:
            err = f"Exception during execution of tool '{tool_id}': {str(exc)}"
            logger.error(f"[TimeoutManager] ERROR: {err}", exc_info=True)
            return False, None, err, exc
