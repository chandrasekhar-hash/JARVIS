"""
Product 1.5 Tool Dispatcher and Mode Selector.
"""
import logging
from typing import Dict, Any, Tuple, Optional, AsyncGenerator
from .models import ToolMetadata, ExecutionContext, ExecutionMode
from .executor import ToolExecutor

logger = logging.getLogger("JARVIS_ToolDispatcher")


class ToolDispatcher:
    """
    Routes execution requests to synchronous, async, streaming, or background handlers.
    """

    @staticmethod
    async def dispatch_execution(
        metadata: ToolMetadata,
        context: ExecutionContext,
        kwargs: Dict[str, Any],
        mode: Optional[ExecutionMode] = None,
    ) -> Tuple[bool, Any, Optional[str], int]:
        """
        Dispatches tool execution to appropriate execution mode worker.
        Returns:
            (success, result_payload, error_message, attempts_count)
        """
        target_mode = mode or (ExecutionMode.STREAMING if metadata.supports_streaming else ExecutionMode.ASYNC)
        logger.info(f"[ToolDispatcher] Dispatching tool '{metadata.tool_id}' under mode '{target_mode.value}'.")

        return await ToolExecutor.execute_handler(metadata, context, kwargs)

    @staticmethod
    async def dispatch_stream(
        metadata: ToolMetadata,
        context: ExecutionContext,
        kwargs: Dict[str, Any],
    ) -> AsyncGenerator[Any, None]:
        """Dispatches streaming execution generator."""
        async for chunk in ToolExecutor.execute_stream(metadata, context, kwargs):
            yield chunk
