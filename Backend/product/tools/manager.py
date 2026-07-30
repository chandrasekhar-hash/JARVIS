"""
Product 1.5 ProductToolExecutionManager Master Orchestrator.
"""
import time
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from .models import (
    ToolMetadata,
    ExecutionContext,
    ToolExecutionResult,
    ExecutionStatusCode,
    ExecutionMetrics,
)
from .metadata import metadata_registry_instance, ToolMetadataRegistry
from .permissions import permission_gateway_instance, ExecutionPermissionGateway
from .context import ExecutionContextFactory
from .dispatcher import ToolDispatcher
from .formatter import ResultFormatter
from .telemetry import (
    telemetry_collector_instance,
    execution_logger_instance,
    ExecutionTelemetryCollector,
    ExecutionLogger,
)

logger = logging.getLogger("JARVIS_ProductToolExecutionManager")


class ProductToolExecutionManager:
    """
    Master Orchestrator for Product 1.5 Tool Execution Engine.
    Coordinates tool selection, permission validation, schema validation,
    context creation, execution dispatching, result formatting, telemetry, and auditing.
    """

    def __init__(
        self,
        metadata_registry: Optional[ToolMetadataRegistry] = None,
        permission_gateway: Optional[ExecutionPermissionGateway] = None,
        telemetry_collector: Optional[ExecutionTelemetryCollector] = None,
        execution_logger: Optional[ExecutionLogger] = None,
    ):
        self.metadata_registry = metadata_registry or metadata_registry_instance
        self.permission_gateway = permission_gateway or permission_gateway_instance
        self.telemetry_collector = telemetry_collector or telemetry_collector_instance
        self.execution_logger = execution_logger or execution_logger_instance

    async def execute_tool(
        self,
        tool_id: str,
        kwargs: Optional[Dict[str, Any]] = None,
        user_id: str = "default_user",
        session_id: Optional[str] = None,
        security_context: Optional[Any] = None,
        user_preferences: Optional[Any] = None,
        memory_provider: Optional[Any] = None,
        plugin_reference: Optional[Any] = None,
        correlation_id: Optional[str] = None,
        request_metadata: Optional[Dict[str, Any]] = None,
    ) -> ToolExecutionResult:
        """
        Main public entry point for tool execution.
        Executes complete 12-stage pipeline and returns standardized ToolExecutionResult.
        """
        start_time = time.time()
        arguments = kwargs or {}

        # 1. Context Creation
        context = ExecutionContextFactory.create_context(
            tool_id=tool_id,
            user_id=user_id,
            session_id=session_id,
            security_context=security_context,
            user_preferences=user_preferences,
            memory_provider=memory_provider,
            plugin_reference=plugin_reference,
            correlation_id=correlation_id,
            request_metadata=request_metadata,
        )

        # 2. Tool Metadata Resolution
        metadata = self.metadata_registry.get_tool_metadata(tool_id)
        if not metadata:
            dur = (time.time() - start_time) * 1000.0
            res = ResultFormatter.format_error(
                context,
                status=ExecutionStatusCode.TOOL_ERROR,
                error_code="TOOL_NOT_FOUND",
                error_message=f"Tool '{tool_id}' not found in registry.",
                duration_ms=dur,
            )
            self._record_telemetry_and_logs(context, res, arguments)
            return res

        # 3. Permission Validation
        authorized, perm_err = self.permission_gateway.authorize_execution(metadata, context, arguments)
        if not authorized:
            dur = (time.time() - start_time) * 1000.0
            res = ResultFormatter.format_error(
                context,
                status=ExecutionStatusCode.PERMISSION_DENIED,
                error_code="PERMISSION_DENIED",
                error_message=perm_err or "Permission denied.",
                duration_ms=dur,
            )
            self._record_telemetry_and_logs(context, res, arguments)
            return res

        # 4. Input Schema Validation
        valid_input, input_err = self.metadata_registry.validate_input(metadata, arguments)
        if not valid_input:
            dur = (time.time() - start_time) * 1000.0
            res = ResultFormatter.format_error(
                context,
                status=ExecutionStatusCode.INVALID_INPUT,
                error_code="INVALID_INPUT",
                error_message=input_err or "Invalid parameters.",
                duration_ms=dur,
            )
            self._record_telemetry_and_logs(context, res, arguments)
            return res

        # 5. Dispatch & Execution
        ok, payload, exec_err, attempts = await ToolDispatcher.dispatch_execution(metadata, context, arguments)
        dur = (time.time() - start_time) * 1000.0

        if not ok:
            status = ExecutionStatusCode.TIMEOUT if "timed out" in (exec_err or "").lower() else ExecutionStatusCode.TOOL_ERROR
            res = ResultFormatter.format_error(
                context,
                status=status,
                error_code=status.value,
                error_message=exec_err or "Tool execution failed.",
                duration_ms=dur,
                attempts=attempts,
            )
            self._record_telemetry_and_logs(context, res, arguments)
            return res

        # 6. Output Schema Validation
        valid_output, output_err = self.metadata_registry.validate_output(metadata, payload)
        if not valid_output:
            logger.warning(f"[ProductToolExecutionManager] Output validation mismatch for tool '{tool_id}': {output_err}")

        # 7. Format Result
        res = ResultFormatter.format_success(
            context,
            payload=payload,
            duration_ms=dur,
            attempts=attempts,
        )
        self._record_telemetry_and_logs(context, res, arguments)
        return res

    async def execute_tool_stream(
        self,
        tool_id: str,
        kwargs: Optional[Dict[str, Any]] = None,
        user_id: str = "default_user",
    ) -> AsyncGenerator[Any, None]:
        """
        Executes tool in streaming mode, yielding partial chunks.
        """
        arguments = kwargs or {}
        context = ExecutionContextFactory.create_context(tool_id=tool_id, user_id=user_id)
        metadata = self.metadata_registry.get_tool_metadata(tool_id)

        if not metadata:
            yield f"Error: Tool '{tool_id}' not found."
            return

        async for chunk in ToolDispatcher.dispatch_stream(metadata, context, arguments):
            yield chunk

    def _record_telemetry_and_logs(
        self,
        context: ExecutionContext,
        result: ToolExecutionResult,
        kwargs: Dict[str, Any],
    ) -> None:
        """Helper to update telemetry collector and audit logs."""
        try:
            self.telemetry_collector.record_execution(result)
            self.execution_logger.log_execution(context, result, kwargs)
        except Exception as e:
            logger.warning(f"[ProductToolExecutionManager] Telemetry/Log recording warning: {e}")

    def get_telemetry_metrics(self) -> ExecutionMetrics:
        """Returns snapshot of engine metrics."""
        return self.telemetry_collector.get_metrics()


# Global singleton instance
tool_execution_manager_instance = ProductToolExecutionManager()
