"""
Product 1.5 Low-Level Tool Executor & Mode Handler.
"""
import asyncio
import inspect
import time
import logging
from typing import Any, Callable, Dict, Tuple, Optional, AsyncGenerator
from .models import ToolMetadata, ExecutionContext, RetryPolicy
from .retry import RetryManager
from .timeout import TimeoutManager

logger = logging.getLogger("JARVIS_ToolExecutor")


class ToolExecutor:
    """
    Low-level worker executing handlers inside timeout watchdogs and retry loops.
    """

    @staticmethod
    def _clean_kwargs(handler: Callable, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Filters kwargs against handler signature to avoid unexpected argument errors."""
        try:
            sig = inspect.signature(handler)
            has_kwargs_param = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
            if not has_kwargs_param:
                return {k: v for k, v in kwargs.items() if k in sig.parameters}
        except Exception:
            pass
        return kwargs

    @staticmethod
    async def execute_handler(
        metadata: ToolMetadata,
        context: ExecutionContext,
        kwargs: Dict[str, Any],
    ) -> Tuple[bool, Any, Optional[str], int]:
        """
        Executes handler with active timeout guards and retry policy.
        Returns:
            (success, result_payload, error_message, attempts_count)
        """
        handler = metadata.handler
        if handler is None:
            return False, None, f"Handler function not found for tool '{metadata.tool_id}'.", 1

        policy = metadata.retry_policy
        attempts = 0
        exec_kwargs = ToolExecutor._clean_kwargs(handler, kwargs)

        while True:
            attempts += 1

            try:
                if inspect.iscoroutinefunction(handler):
                    coro = handler(**exec_kwargs)
                    ok, res, err, exc = await TimeoutManager.execute_with_timeout(
                        coro, timeout_seconds=metadata.timeout_seconds, tool_id=metadata.tool_id
                    )
                else:
                    loop = asyncio.get_running_loop()
                    func_call = lambda: handler(**exec_kwargs)
                    coro = loop.run_in_executor(None, func_call)
                    ok, res, err, exc = await TimeoutManager.execute_with_timeout(
                        coro, timeout_seconds=metadata.timeout_seconds, tool_id=metadata.tool_id
                    )

                if ok:
                    return True, res, None, attempts
                else:
                    # Execution failed / timed out
                    should_retry, delay = RetryManager.should_retry(
                        policy, attempts, exc or RuntimeError(err or "Execution failed")
                    )
                    if should_retry:
                        await asyncio.sleep(delay)
                        continue
                    return False, None, err, attempts

            except Exception as e:
                err_msg = f"Unhandled exception during execution of tool '{metadata.tool_id}': {str(e)}"
                logger.error(f"[ToolExecutor] {err_msg}", exc_info=True)
                should_retry, delay = RetryManager.should_retry(policy, attempts, e)
                if should_retry:
                    await asyncio.sleep(delay)
                    continue
                return False, None, err_msg, attempts

    @staticmethod
    async def execute_stream(
        metadata: ToolMetadata,
        context: ExecutionContext,
        kwargs: Dict[str, Any],
    ) -> AsyncGenerator[Any, None]:
        """
        Yields partial execution tokens asynchronously for streaming tools.
        """
        handler = metadata.handler
        if handler is None or not inspect.isasyncgenfunction(handler):
            yield f"Error: Tool '{metadata.tool_id}' does not support streaming execution."
            return

        exec_kwargs = ToolExecutor._clean_kwargs(handler, kwargs)
        async for chunk in handler(**exec_kwargs):
            yield chunk
