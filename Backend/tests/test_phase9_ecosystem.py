import os
import sys
import unittest
import asyncio

from Backend.plugins.sandbox import PluginSandbox, ResourceQuota
from Backend.plugins.permissions import PermissionEngine
from Backend.plugins.lifecycle import PluginLifecycleManager, ExtendedPluginStatus
from jarvis_sdk.plugin import jarvis_plugin, jarvis_tool, BaseJarvisPlugin
from jarvis_sdk.testing import PluginTestHarness
from Cloud.marketplace.package_verifier import PackageVerifier
from Cloud.marketplace.service import MarketplaceService
from Cloud.webhooks.service import WebhookService
from Backend.autonomous.workflow_engine import WorkflowEngine, WorkflowDefinition, WorkflowNode


@jarvis_plugin(
    plugin_id="plg_sample_test",
    name="Sample Test Plugin",
    version="1.0.0",
    sdk_version="1.0",
    api_version="1",
    minimum_runtime="1.0.0",
    capabilities=["fs:read", "net:outbound"]
)
class SampleTestPlugin(BaseJarvisPlugin):
    @jarvis_tool(name="calculate_sum", description="Calculates the sum of two integers")
    def calculate_sum(self, a: int, b: int) -> int:
        return a + b


class TestPhase9Ecosystem(unittest.TestCase):

    def setUp(self):
        self.plugin_id = "plg_sample_test"

    def test_01_jarvis_sdk_decorators_and_harness(self):
        harness = PluginTestHarness(SampleTestPlugin)
        manifest = harness.get_manifest()

        self.assertEqual(manifest["id"], self.plugin_id)
        self.assertEqual(manifest["version"], "1.0.0")

        tools = harness.get_registered_tools()
        self.assertIn("calculate_sum", tools)

        res = harness.invoke_tool("calculate_sum", a=10, b=15)
        self.assertEqual(res, 25)

    def test_02_permission_engine_capabilities(self):
        pe = PermissionEngine()
        pe.grant_permissions(self.plugin_id, ["fs:read", "net:outbound"])

        self.assertTrue(pe.check_permission(self.plugin_id, "fs:read"))
        self.assertTrue(pe.check_permission(self.plugin_id, "net:outbound"))
        self.assertFalse(pe.check_permission(self.plugin_id, "system:exec"))

    def test_03_plugin_lifecycle_state_machine_and_hooks(self):
        async def run_test():
            plm = PluginLifecycleManager()
            hook_ran = []

            async def sample_hook():
                hook_ran.append("on_enable")

            await plm.install_plugin(self.plugin_id)
            self.assertEqual(plm.plugin_states[self.plugin_id], ExtendedPluginStatus.INSTALLED)

            await plm.enable_plugin(self.plugin_id, hook_func=sample_hook)
            self.assertEqual(plm.plugin_states[self.plugin_id], ExtendedPluginStatus.ENABLED)
            self.assertIn("on_enable", hook_ran)

            await plm.disable_plugin(self.plugin_id)
            self.assertEqual(plm.plugin_states[self.plugin_id], ExtendedPluginStatus.DISABLED)

        asyncio.run(run_test())

    def test_04_marketplace_package_verifier_and_service(self):
        ms = MarketplaceService()
        item = ms.publish_plugin(
            publisher_id="usr_dev_123",
            name="Slack Dispatcher",
            version="1.0.0",
            sdk_version="1.0",
            api_version="1",
            minimum_runtime="1.0.0",
            category="productivity",
            description="Dispatches alerts to Slack.",
            capabilities=["net:outbound"],
            package_url="https://cloud.jarvis.ai/packages/slack.jpx",
            signature_b64="dGVzdF9zaWduYXR1cmU="
        )
        self.assertEqual(item["name"], "Slack Dispatcher")

        valid, msg = PackageVerifier.validate_manifest_compatibility(item, current_runtime_version="2.5.0")
        self.assertTrue(valid)

    def test_05_webhook_service_hmac_and_dispatch(self):
        async def run_test():
            ws = WebhookService()
            sub = ws.register_subscription(
                user_id="usr_test_123",
                event_type="task_completed",
                target_url="https://api.external.com/webhook",
                secret_token="sec_supersecret_token_123"
            )
            self.assertEqual(sub["status"], "active")

            dispatched = await ws.dispatch_event(
                user_id="usr_test_123",
                event_type="task_completed",
                payload={"task_id": "tsk_99", "status": "COMPLETED"}
            )
            self.assertEqual(len(dispatched), 1)
            self.assertTrue(dispatched[0]["signature"].startswith("sha256="))

        asyncio.run(run_test())

    def test_06_durable_workflow_engine_dag(self):
        async def run_test():
            we = WorkflowEngine()
            wf = WorkflowDefinition(
                workflow_id="wf_morning_routine",
                name="Morning Routine Automation",
                entry_node_id="node_1",
                nodes={
                    "node_1": WorkflowNode(
                        node_id="node_1",
                        node_type="trigger",
                        action_name="check_time",
                        next_nodes=["node_2"]
                    ),
                    "node_2": WorkflowNode(
                        node_id="node_2",
                        node_type="action",
                        action_name="fetch_weather",
                        next_nodes=[]
                    )
                }
            )
            we.register_workflow(wf)
            exec_state = await we.execute_workflow("wf_morning_routine", trigger_context={"time": "08:00"})
            self.assertEqual(exec_state.status, "COMPLETED")
            self.assertIn("node_1", exec_state.node_outputs)
            self.assertIn("node_2", exec_state.node_outputs)

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
