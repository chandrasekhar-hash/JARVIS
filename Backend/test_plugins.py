import unittest
import os
import sys
import json
from fastapi.testclient import TestClient

from plugins.plugin_validator import PluginValidator
from plugins.plugin_manager import PluginManager
from plugins.plugin_models import PluginStatus
from tools.registry import registry as tool_registry
from main import app

class TestDynamicLocalPluginFramework(unittest.TestCase):

    def setUp(self):
        self.manager = PluginManager(plugins_dir="Backend/plugins_installed")
        self.client = TestClient(app)

    def test_01_manifest_validation(self):
        valid_dict = {
            "id": "test_plugin_valid",
            "name": "Test Valid Plugin",
            "description": "A valid test plugin manifest",
            "permissions": ["network", "filesystem"],
            "entry": "main.py"
        }
        valid, manifest, err = PluginValidator.validate_manifest_dict(valid_dict, "Backend/plugins_installed/sample_weather_plugin")
        self.assertTrue(valid)
        self.assertIsNotNone(manifest)
        self.assertEqual(manifest.id, "test_plugin_valid")

        # Invalid manifest missing required field
        invalid_dict = {"name": "No ID Plugin", "description": "Missing ID"}
        valid2, manifest2, err2 = PluginValidator.validate_manifest_dict(invalid_dict, "Backend/plugins_installed/sample_weather_plugin")
        self.assertFalse(valid2)
        self.assertIn("missing required field", err2.lower())

    def test_02_plugin_discovery_and_loading(self):
        plugins = self.manager.discover_and_load_plugins()
        self.assertGreater(len(plugins), 0)
        
        # Verify weather plugin loaded
        weather_plugin = self.manager.get_plugin("sample_weather_plugin")
        self.assertIsNotNone(weather_plugin)
        self.assertIn(weather_plugin.status, [PluginStatus.RUNNING, PluginStatus.LOADED])
        self.assertIn("get_local_weather", weather_plugin.registered_tools)
        
        # Verify tool was registered in tool_registry
        self.assertIn("get_local_weather", tool_registry.tools)

    def test_03_plugin_lifecycle_enable_disable_reload(self):
        self.manager.discover_and_load_plugins()
        plugin_id = "sample_weather_plugin"

        # 1. Disable plugin
        dis_ok = self.manager.disable_plugin(plugin_id)
        self.assertTrue(dis_ok)
        plugin = self.manager.get_plugin(plugin_id)
        self.assertEqual(plugin.status, PluginStatus.DISABLED)
        self.assertNotIn("get_local_weather", tool_registry.tools)

        # 2. Enable plugin
        en_ok = self.manager.enable_plugin(plugin_id)
        self.assertTrue(en_ok)
        plugin = self.manager.get_plugin(plugin_id)
        self.assertEqual(plugin.status, PluginStatus.RUNNING)
        self.assertIn("get_local_weather", tool_registry.tools)

        # 3. Reload plugin
        rel_ok = self.manager.reload_plugin(plugin_id)
        self.assertTrue(rel_ok)
        self.assertIn("get_local_weather", tool_registry.tools)

    def test_04_fault_isolation(self):
        # Create a broken manifest dictionary
        broken_dir = "Backend/plugins_installed/broken_test_plugin"
        os.makedirs(broken_dir, exist_ok=True)
        with open(os.path.join(broken_dir, "plugin.json"), "w") as f:
            json.dump({
                "id": "broken_test_plugin",
                "name": "Broken Plugin",
                "description": "Intentionally broken syntax plugin",
                "entry": "main.py"
            }, f)
            
        with open(os.path.join(broken_dir, "main.py"), "w") as f:
            f.write("INVALID PYTHON SYNTAX = === 123")

        try:
            # Loading broken plugin must NOT crash discovery/backend
            plugins = self.manager.discover_and_load_plugins()
            broken_state = self.manager.get_plugin("broken_test_plugin")
            self.assertIsNotNone(broken_state)
            self.assertEqual(broken_state.status, PluginStatus.FAILED)
            self.assertFalse(broken_state.health_ok)
        finally:
            # Cleanup broken test folder
            if os.path.exists(broken_dir):
                import shutil
                shutil.rmtree(broken_dir, ignore_errors=True)

    def test_05_rest_api_endpoints(self):
        self.manager.discover_and_load_plugins()

        # 1. GET /api/plugins
        r1 = self.client.get("/api/plugins")
        self.assertEqual(r1.status_code, 200)
        self.assertIn("plugins", r1.json())
        self.assertGreater(len(r1.json()["plugins"]), 0)

        # 2. GET /api/plugins/{id}
        r2 = self.client.get("/api/plugins/sample_weather_plugin")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["plugin"]["plugin_id"], "sample_weather_plugin")

        # 3. POST /api/plugins/{id}/disable
        r3 = self.client.post("/api/plugins/sample_weather_plugin/disable")
        self.assertEqual(r3.status_code, 200)

        # 4. POST /api/plugins/{id}/enable
        r4 = self.client.post("/api/plugins/sample_weather_plugin/enable")
        self.assertEqual(r4.status_code, 200)

        # 5. POST /api/plugins/{id}/reload
        r5 = self.client.post("/api/plugins/sample_weather_plugin/reload")
        self.assertEqual(r5.status_code, 200)

        # 6. GET /api/plugins/{id}/health
        r6 = self.client.get("/api/plugins/sample_weather_plugin/health")
        self.assertEqual(r6.status_code, 200)
        self.assertTrue(r6.json()["health_ok"])


if __name__ == "__main__":
    unittest.main()
