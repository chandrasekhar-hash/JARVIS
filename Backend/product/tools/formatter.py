"""
Product 1.5 Tool Execution Result Formatter and Envelope Constructor.
"""
import time
import logging
from typing import Any, Optional
from .models import ToolExecutionResult, ExecutionStatusCode, ExecutionContext

logger = logging.getLogger("JARVIS_ResultFormatter")


class ResultFormatter:
    """
    Constructs standardized ToolExecutionResult envelopes for all execution statuses.
    """

    @staticmethod
    def format_success(
        context: ExecutionContext,
        payload: Any,
        duration_ms: float,
        attempts: int = 1,
    ) -> ToolExecutionResult:
        """Constructs a success result envelope."""
        return ToolExecutionResult(
            correlation_id=context.correlation_id,
            tool_id=context.tool_id,
            status=ExecutionStatusCode.SUCCESS,
            success=True,
            result_payload=payload,
            duration_ms=duration_ms,
            attempts=attempts,
            timestamp=time.time(),
        )

    @staticmethod
    def format_error(
        context: ExecutionContext,
        status: ExecutionStatusCode,
        error_code: str,
        error_message: str,
        duration_ms: float,
        attempts: int = 1,
    ) -> ToolExecutionResult:
        """Constructs an error result envelope."""
        return ToolExecutionResult(
            correlation_id=context.correlation_id,
            tool_id=context.tool_id,
            status=status,
            success=False,
            result_payload=None,
            error_code=error_code,
            error_message=error_message,
            duration_ms=duration_ms,
            attempts=attempts,
            timestamp=time.time(),
        )
