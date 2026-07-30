"""
Comprehensive Unit & Integration Test Suite for J.A.R.V.I.S. Phase P1.4 (Plugin & Skills Framework).
Covers Manifest Validation, Dependency DAG Resolution, Plugin Lifecycle State Machine,
Zero-Trust Permission Model, Configuration Engine, Skills Registry, Error Isolation & Circuit Breaker,
and Health Telemetry.
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

from product.plugins import (
    ProductPluginManager,
    PluginState,
    PluginStatus,
    PluginManifest,
    PluginPermissionScope,
    PermissionConsentStatus,
    PluginCategory,
    PluginValidator,
    PluginPermissionEngine,
    PermissionDeniedException,
    PluginConfigEngine,
    PluginAPIContext,
    PluginLifecycleManager,
    PluginIsolationGuard,
)
from brain.event_bus import event_bus


class TestProductPhaseP14(unittest.TestCase):
    """
    Dedicated test suite for Phase P1.4 Plugin & Skills Framework.
    """

    def setUp(self):
        """Set up temporary plugin storage directory and manager instance."""
        from product.plugins.registry import (
            plugin_registry_instance,
            skills_registry_instance,
            command_registry_instance,
        )
        plugin_registry_instance._plugins.clear()
        skills_registry_instance._skills.clear()
        command_registry_instance._commands.clear()

        self.test_dir = tempfile.mkdtemp(prefix="jarvis_p14_test_plugins_")
        self.manager = ProductPluginManager(plugins_dir=self.test_dir, event_bus=event_bus)

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """Clean up temporary directories, loaded plugins, and asyncio event loop."""
        from product.plugins.registry import (
            plugin_registry_instance,
            skills_registry_instance,
            command_registry_instance,
        )

        for state in list(self.manager.get_all_plugins()):
            self.manager.unload_plugin(state.plugin_id)

        plugin_registry_instance._plugins.clear()
        skills_registry_instance._skills.clear()
        command_registry_instance._commands.clear()

        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

        self.loop.close()

    def _create_test_plugin(
        self,
        plugin_id: str,
        manifest_data: dict,
        main_py_code: str = "",
    ) -> str:
        """Helper to create a test plugin folder on disk."""
        folder = os.path.join(self.test_dir, plugin_id)
        os.makedirs(folder, exist_ok=True)

        # Write plugin.json
        import json
        with open(os.path.join(folder, "plugin.json"), "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        # Write main.py
        with open(os.path.join(folder, manifest_data.get("entry_point", "main.py")), "w", encoding="utf-8") as f:
            f.write(main_py_code)

        return folder

    # -------------------------------------------------------------------------
    # 1. Manifest Specification & Validation Tests
    # -------------------------------------------------------------------------
    def test_01_manifest_validation_valid(self):
        manifest_dict = {
            "id": "sample_weather",
            "name": "Sample Weather Plugin",
            "version": "1.2.0",
            "author": "DeepMind Team",
            "description": "Provides weather forecasts",
            "permissions": ["network.http", "notifications"],
            "minimum_jarvis_version": "1.0.0",
            "category": "information",
        }
        valid, manifest, err = PluginValidator.validate_manifest_dict(manifest_dict)
        self.assertTrue(valid)
        self.assertIsNotNone(manifest)
        self.assertIsNone(err)
        self.assertEqual(manifest.id, "sample_weather")
        self.assertEqual(manifest.category, "information")

    def test_02_manifest_validation_invalid_id_and_semver(self):
        # Invalid plugin ID (spaces not allowed)
        bad_id = {
            "id": "Invalid ID",
            "name": "Bad Plugin",
            "version": "1.0.0",
            "author": "Tester",
            "description": "Desc",
        }
        valid, _, err = PluginValidator.validate_manifest_dict(bad_id)
        self.assertFalse(valid)
        self.assertIn("Invalid or missing plugin 'id'", err)

        # Invalid SemVer
        bad_ver = {
            "id": "valid_id",
            "name": "Bad Ver Plugin",
            "version": "v1.0",
            "author": "Tester",
            "description": "Desc",
        }
        valid, _, err = PluginValidator.validate_manifest_dict(bad_ver)
        self.assertFalse(valid)
        self.assertIn("Invalid plugin version format", err)

    def test_03_minimum_jarvis_version_enforcement(self):
        incompatible_manifest = {
            "id": "future_plugin",
            "name": "Future Plugin",
            "version": "1.0.0",
            "author": "Tester",
            "description": "Requires future JARVIS",
            "minimum_jarvis_version": "9.0.0",  # Higher than current 1.4.0
        }
        valid, _, err = PluginValidator.validate_manifest_dict(incompatible_manifest, current_jarvis_version="1.4.0")
        self.assertFalse(valid)
        self.assertIn("requires JARVIS version >=", err)

    # -------------------------------------------------------------------------
    # 2. Dependency Resolution DAG Tests
    # -------------------------------------------------------------------------
    def test_04_dependency_dag_resolution_success(self):
        manifest_a = PluginManifest(id="plugin_a", name="A", version="1.0.0", author="T", description="D")
        manifest_b = PluginManifest(id="plugin_b", name="B", version="1.0.0", author="T", description="D", dependencies={"plugin_a": "^1.0.0"})
        manifest_c = PluginManifest(id="plugin_c", name="C", version="1.0.0", author="T", description="D", dependencies={"plugin_b": "^1.0.0"})

        state_a = PluginState(plugin_id="plugin_a", manifest=manifest_a, plugin_dir="/tmp/a")
        state_b = PluginState(plugin_id="plugin_b", manifest=manifest_b, plugin_dir="/tmp/b")
        state_c = PluginState(plugin_id="plugin_c", manifest=manifest_c, plugin_dir="/tmp/c")

        # Reverse order to verify topological sort
        states = [state_c, state_b, state_a]
        ok, sorted_ids, err = PluginValidator.resolve_dependencies_dag(states)

        self.assertTrue(ok)
        self.assertIsNone(err)
        # Order must be plugin_a -> plugin_b -> plugin_c
        self.assertEqual(sorted_ids, ["plugin_a", "plugin_b", "plugin_c"])

    def test_05_dependency_dag_circular_dependency_detection(self):
        manifest_x = PluginManifest(id="plugin_x", name="X", version="1.0.0", author="T", description="D", dependencies={"plugin_y": "^1.0.0"})
        manifest_y = PluginManifest(id="plugin_y", name="Y", version="1.0.0", author="T", description="D", dependencies={"plugin_x": "^1.0.0"})

        state_x = PluginState(plugin_id="plugin_x", manifest=manifest_x, plugin_dir="/tmp/x")
        state_y = PluginState(plugin_id="plugin_y", manifest=manifest_y, plugin_dir="/tmp/y")

        ok, sorted_ids, err = PluginValidator.resolve_dependencies_dag([state_x, state_y])
        self.assertFalse(ok)
        self.assertIn("Circular dependency detected", err)

    # -------------------------------------------------------------------------
    # 3. Plugin Lifecycle State Machine & Discovery Tests
    # -------------------------------------------------------------------------
    def test_06_plugin_discovery_and_lifecycle(self):
        manifest = {
            "id": "calculator_plugin",
            "name": "Calculator Skill Plugin",
            "version": "1.0.0",
            "author": "UnitTester",
            "description": "Math calculation skill",
            "permissions": [],
            "minimum_jarvis_version": "1.0.0",
        }
        code = """
initialized = False
activated = False

def on_initialize(context):
    global initialized
    initialized = True
    context.register_skill(
        skill_id="add",
        name="Add Numbers",
        description="Adds two numbers",
        handler=lambda a, b: a + b
    )

def on_activate():
    global activated
    activated = True
"""
        self._create_test_plugin("calculator_plugin", manifest, code)

        discovered = self.manager.discover_and_load_plugins()
        self.assertEqual(len(discovered), 1)

        state = self.manager.get_plugin("calculator_plugin")
        self.assertIsNotNone(state)
        self.assertEqual(state.status, PluginStatus.ACTIVATED)

        # Check skill registration
        skill = self.manager.skills_registry.get_skill("calculator_plugin.add")
        self.assertIsNotNone(skill)
        self.assertEqual(skill.handler(5, 7), 12)

        # Execute skill via isolation guard
        async def run_test():
            ok, res, err = await self.manager.execute_skill("calculator_plugin", "add", 10, 20)
            self.assertTrue(ok)
            self.assertEqual(res, 30)
            self.assertIsNone(err)

        self.loop.run_until_complete(run_test())

        # Test disable and unload
        self.assertTrue(self.manager.disable_plugin("calculator_plugin"))
        self.assertEqual(self.manager.get_plugin("calculator_plugin").status, PluginStatus.DISABLED)

        self.assertTrue(self.manager.unload_plugin("calculator_plugin"))
        self.assertEqual(self.manager.get_plugin("calculator_plugin").status, PluginStatus.UNLOADED)

    # -------------------------------------------------------------------------
    # 4. Zero-Trust Permission Model Tests
    # -------------------------------------------------------------------------
    def test_07_permission_engine_enforcement(self):
        engine = PluginPermissionEngine()
        manifest = PluginManifest(
            id="file_manager",
            name="File Manager",
            version="1.0.0",
            author="Tester",
            description="Reads files",
            permissions=["filesystem.read"],
        )

        engine.initialize_plugin_permissions("file_manager", manifest)

        # Declared scope -> Allowed
        self.assertTrue(engine.check_permission("file_manager", manifest, "filesystem.read"))

        # Undeclared scope -> Exception
        with self.assertRaises(PermissionDeniedException):
            engine.check_permission("file_manager", manifest, "filesystem.write")

        # Explicit user denial
        engine.set_permission_status("file_manager", "filesystem.read", PermissionConsentStatus.DENIED)
        with self.assertRaises(PermissionDeniedException):
            engine.check_permission("file_manager", manifest, "filesystem.read")

    # -------------------------------------------------------------------------
    # 5. Configuration Engine Tests
    # -------------------------------------------------------------------------
    def test_08_plugin_config_engine_defaults_and_overrides(self):
        config_engine = PluginConfigEngine()
        manifest = PluginManifest(
            id="translator",
            name="Translator",
            version="1.0.0",
            author="Tester",
            description="Translation",
            configuration_schema={
                "target_language": {"type": "string", "default": "es"},
                "timeout": {"type": "integer", "default": 5},
            },
        )

        # Default fallback
        lang_default = config_engine.get_setting("translator", manifest, "target_language")
        self.assertEqual(lang_default, "es")

        # Set valid override
        self.assertTrue(config_engine.set_setting("translator", manifest, "target_language", "fr"))
        lang_override = config_engine.get_setting("translator", manifest, "target_language")
        self.assertEqual(lang_override, "fr")

        # Invalid type set attempt -> Exception
        with self.assertRaises(ValueError):
            config_engine.set_setting("translator", manifest, "target_language", 12345)

    # -------------------------------------------------------------------------
    # 6. Error Isolation & Circuit Breaker Tests
    # -------------------------------------------------------------------------
    def test_09_error_isolation_and_circuit_breaker(self):
        manifest = PluginManifest(
            id="flaky_plugin",
            name="Flaky Plugin",
            version="1.0.0",
            author="Tester",
            description="Fails repeatedly",
        )
        state = PluginState(plugin_id="flaky_plugin", manifest=manifest, status=PluginStatus.ACTIVATED, plugin_dir="/tmp/flaky")

        def crashing_handler():
            raise RuntimeError("Simulated third-party bug!")

        async def run_circuit_breaker_test():
            # Run failing calls up to max consecutive threshold (5)
            for i in range(5):
                ok, res, err = await PluginIsolationGuard.execute_async(state, crashing_handler)
                self.assertFalse(ok)
                self.assertIsNone(res)
                self.assertIn("Simulated third-party bug", err)

            # Assert Circuit Breaker tripped
            self.assertEqual(state.status, PluginStatus.FAILED)
            self.assertFalse(state.health_ok)
            self.assertEqual(state.consecutive_failures, 5)

        self.loop.run_until_complete(run_circuit_breaker_test())

    def test_10_execution_timeout_isolation(self):
        manifest = PluginManifest(
            id="slow_plugin",
            name="Slow Plugin",
            version="1.0.0",
            author="Tester",
            description="Infinite loop",
        )
        state = PluginState(plugin_id="slow_plugin", manifest=manifest, status=PluginStatus.ACTIVATED, plugin_dir="/tmp/slow")

        async def infinite_loop_handler():
            await asyncio.sleep(100)

        async def run_timeout_test():
            ok, res, err = await PluginIsolationGuard.execute_async(state, infinite_loop_handler, timeout_seconds=0.1)
            self.assertFalse(ok)
            self.assertIsNone(res)
            self.assertIn("timed out", err)

        self.loop.run_until_complete(run_timeout_test())

    # -------------------------------------------------------------------------
    # 7. Plugin Health Telemetry Tests
    # -------------------------------------------------------------------------
    def test_11_plugin_health_telemetry(self):
        manifest_1 = {
            "id": "plugin_one",
            "name": "P1",
            "version": "1.0.0",
            "author": "A",
            "description": "D",
        }
        self._create_test_plugin("plugin_one", manifest_1, "# Empty main.py")

        self.manager.discover_and_load_plugins()
        health = self.manager.get_plugin_health()

        self.assertEqual(health["total_plugins"], 1)
        self.assertEqual(health["active_plugins"], 1)
        self.assertEqual(health["failed_plugins"], 0)


if __name__ == "__main__":
    unittest.main()
