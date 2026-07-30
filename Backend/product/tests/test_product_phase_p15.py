"""
Comprehensive Unit & Integration Test Suite for J.A.R.V.I.S. Phase P1.5 (Tool Execution Engine).
Covers Tool Metadata Registration, Schema Validation, Permission Gateway, Execution Modes,
Timeout Watchdogs, Retry Strategies, Error Formatting, Telemetry, and Logging.
"""
import os
import sys
import time
import shutil
import tempfile
import unittest
import asyncio

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from product.tools import (
    ProductToolExecutionManager,
    ToolMetadata,
    ExecutionContext,
    ToolExecutionResult,
    ExecutionStatusCode,
    RetryPolicy,
    RetryPolicyType,
    ToolCategory,
    ToolMetadataRegistry,
    ExecutionPermissionGateway,
    ExecutionTelemetryCollector,
    ExecutionLogger,
)


class TestProductPhaseP15(unittest.TestCase):
    """
    Dedicated unit and integration test suite for Phase P1.5 Tool Execution Engine.
    """

    def setUp(self):
        """Set up in-memory registry, permission gateway, telemetry, and manager instances."""
        self.test_log_dir = tempfile.mkdtemp(prefix="jarvis_p15_logs_")
        self.metadata_registry = ToolMetadataRegistry()
        self.permission_gateway = ExecutionPermissionGateway()
        self.telemetry = ExecutionTelemetryCollector()
        self.logger = ExecutionLogger(log_dir=self.test_log_dir)

        self.manager = ProductToolExecutionManager(
            metadata_registry=self.metadata_registry,
            permission_gateway=self.permission_gateway,
            telemetry_collector=self.telemetry,
            execution_logger=self.logger,
        )

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """Clean up temporary log directory and asyncio event loop."""
        if os.path.exists(self.test_log_dir):
            shutil.rmtree(self.test_log_dir, ignore_errors=True)
        self.loop.close()

    # -------------------------------------------------------------------------
    # 1. Metadata Registration & Schema Validation Tests
    # -------------------------------------------------------------------------
    def test_01_tool_metadata_registration_and_validation(self):
        def sample_add(a: int, b: int) -> int:
            return a + b

        meta = ToolMetadata(
            tool_id="math.add",
            name="Add Numbers",
            description="Adds two integers",
            category=ToolCategory.UTILITY,
            input_schema={
                "type": "object",
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"},
                },
                "required": ["a", "b"],
            },
            handler=sample_add,
        )

        self.assertTrue(self.manager.metadata_registry.register_tool_metadata(meta))

        # Valid input check
        ok, err = self.manager.metadata_registry.validate_input(meta, {"a": 5, "b": 10})
        self.assertTrue(ok)
        self.assertIsNone(err)

        # Missing required parameter check
        ok, err = self.manager.metadata_registry.validate_input(meta, {"a": 5})
        self.assertFalse(ok)
        self.assertIn("Missing required parameter 'b'", err)

        # Parameter type mismatch check
        ok, err = self.manager.metadata_registry.validate_input(meta, {"a": "invalid_string", "b": 10})
        self.assertFalse(ok)
        self.assertIn("Parameter 'a' expects numeric", err)

    # -------------------------------------------------------------------------
    # 2. Synchronous & Asynchronous Execution Pipeline Tests
    # -------------------------------------------------------------------------
    def test_02_sync_tool_execution(self):
        def multiply(x: int, y: int) -> int:
            return x * y

        meta = ToolMetadata(
            tool_id="math.multiply",
            name="Multiply",
            description="Multiplies numbers",
            handler=multiply,
        )
        self.manager.metadata_registry.register_tool_metadata(meta)

        async def run_test():
            res = await self.manager.execute_tool("math.multiply", kwargs={"x": 6, "y": 7})
            self.assertTrue(res.success)
            self.assertEqual(res.status, ExecutionStatusCode.SUCCESS)
            self.assertEqual(res.result_payload, 42)
            self.assertGreater(res.duration_ms, 0.0)

        self.loop.run_until_complete(run_test())

    def test_03_async_tool_execution(self):
        async def async_fetch_data(endpoint: str) -> dict:
            await asyncio.sleep(0.01)
            return {"status": "ok", "endpoint": endpoint}

        meta = ToolMetadata(
            tool_id="net.fetch",
            name="Fetch Data",
            description="Fetches async data",
            supports_async=True,
            handler=async_fetch_data,
        )
        self.manager.metadata_registry.register_tool_metadata(meta)

        async def run_test():
            res = await self.manager.execute_tool("net.fetch", kwargs={"endpoint": "/api/v1"})
            self.assertTrue(res.success)
            self.assertEqual(res.result_payload, {"status": "ok", "endpoint": "/api/v1"})

        self.loop.run_until_complete(run_test())

    # -------------------------------------------------------------------------
    # 3. Permission Gateway Enforcement Tests
    # -------------------------------------------------------------------------
    def test_04_permission_gateway_confirmation_required(self):
        def delete_file(path: str) -> str:
            return f"Deleted {path}"

        meta = ToolMetadata(
            tool_id="fs.delete",
            name="Delete File",
            description="Deletes file",
            safety_level="confirmation_required",
            handler=delete_file,
        )
        self.manager.metadata_registry.register_tool_metadata(meta)

        async def run_test():
            # Execution without confirmation -> DENIED
            res_denied = await self.manager.execute_tool("fs.delete", kwargs={"path": "/tmp/test.txt"})
            self.assertFalse(res_denied.success)
            self.assertEqual(res_denied.status, ExecutionStatusCode.PERMISSION_DENIED)
            self.assertIn("requires user confirmation", res_denied.error_message)

            # Execution with confirmed=True -> SUCCESS
            res_allowed = await self.manager.execute_tool("fs.delete", kwargs={"path": "/tmp/test.txt", "confirmed": True})
            self.assertTrue(res_allowed.success)
            self.assertEqual(res_allowed.result_payload, "Deleted /tmp/test.txt")

        self.loop.run_until_complete(run_test())

    # -------------------------------------------------------------------------
    # 4. Timeout Watchdog Tests
    # -------------------------------------------------------------------------
    def test_05_timeout_watchdog(self):
        async def slow_operation() -> str:
            await asyncio.sleep(5.0)
            return "Done"

        meta = ToolMetadata(
            tool_id="system.slow",
            name="Slow Operation",
            description="Times out",
            timeout_seconds=0.1,  # 100ms timeout
            handler=slow_operation,
        )
        self.manager.metadata_registry.register_tool_metadata(meta)

        async def run_test():
            res = await self.manager.execute_tool("system.slow")
            self.assertFalse(res.success)
            self.assertEqual(res.status, ExecutionStatusCode.TIMEOUT)
            self.assertIn("timed out", res.error_message)

        self.loop.run_until_complete(run_test())

    # -------------------------------------------------------------------------
    # 5. Retry Strategy & Exponential Backoff Tests
    # -------------------------------------------------------------------------
    def test_06_exponential_backoff_retry_strategy(self):
        attempts_counter = 0

        def flaky_service() -> str:
            nonlocal attempts_counter
            attempts_counter += 1
            if attempts_counter < 3:
                raise ConnectionError("Temporary network glitch")
            return "Connected"

        meta = ToolMetadata(
            tool_id="net.connect",
            name="Flaky Connect",
            description="Retries on failure",
            retry_policy=RetryPolicy(
                policy_type=RetryPolicyType.EXPONENTIAL_BACKOFF,
                max_retries=3,
                initial_delay_seconds=0.01,
                backoff_factor=1.5,
                retryable_exceptions=["ConnectionError"],
            ),
            handler=flaky_service,
        )
        self.manager.metadata_registry.register_tool_metadata(meta)

        async def run_test():
            res = await self.manager.execute_tool("net.connect")
            self.assertTrue(res.success)
            self.assertEqual(res.result_payload, "Connected")
            self.assertEqual(res.attempts, 3)

        self.loop.run_until_complete(run_test())

    # -------------------------------------------------------------------------
    # 6. Streaming Mode Execution Tests
    # -------------------------------------------------------------------------
    def test_07_streaming_execution_mode(self):
        async def stream_generator(tokens: list):
            for t in tokens:
                await asyncio.sleep(0.01)
                yield t

        meta = ToolMetadata(
            tool_id="ai.synthesize",
            name="AI Synthesizer",
            description="Streams tokens",
            supports_streaming=True,
            handler=stream_generator,
        )
        self.manager.metadata_registry.register_tool_metadata(meta)

        async def run_test():
            collected = []
            async for chunk in self.manager.execute_tool_stream("ai.synthesize", kwargs={"tokens": ["Hello", " ", "World"]}):
                collected.append(chunk)

            self.assertEqual(collected, ["Hello", " ", "World"])

        self.loop.run_until_complete(run_test())

    # -------------------------------------------------------------------------
    # 7. Telemetry & Metrics Collection Tests
    # -------------------------------------------------------------------------
    def test_08_telemetry_metrics_collection(self):
        def ping() -> str:
            return "pong"

        meta = ToolMetadata(tool_id="net.ping", name="Ping", description="Ping", handler=ping)
        self.manager.metadata_registry.register_tool_metadata(meta)

        async def run_test():
            await self.manager.execute_tool("net.ping")
            await self.manager.execute_tool("net.ping")

            metrics = self.manager.get_telemetry_metrics()
            self.assertEqual(metrics.total_executions, 2)
            self.assertEqual(metrics.successful_executions, 2)
            self.assertEqual(metrics.failed_executions, 0)
            self.assertEqual(metrics.tool_usage_counts.get("net.ping"), 2)

        self.loop.run_until_complete(run_test())


if __name__ == "__main__":
    unittest.main()
