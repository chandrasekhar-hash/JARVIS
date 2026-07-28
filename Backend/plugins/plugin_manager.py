import os
import json
from typing import List, Dict, Any, Optional
from plugins.plugin_models import PluginState, PluginStatus
from plugins.plugin_validator import PluginValidator
from plugins.plugin_lifecycle import PluginLifecycleManager
from plugins.plugin_registry import plugin_registry_instance
from tools.telemetry import log_structured, backend_log

class PluginManager:
    """
    High-level orchestrator for discovering, validating, loading, and managing local plugins
    installed under Backend/plugins_installed/.
    """

    def __init__(self, plugins_dir: str = "Backend/plugins_installed"):
        candidates = [
            plugins_dir,
            "Backend/plugins_installed",
            "plugins_installed",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugins_installed")
        ]
        chosen = plugins_dir
        for c in candidates:
            if os.path.exists(c) and os.listdir(c):
                chosen = c
                break
            elif os.path.exists(c):
                chosen = c
        self.plugins_dir = chosen

    def discover_and_load_plugins(self) -> List[PluginState]:
        """
        Scans Backend/plugins_installed/ for plugin folders containing plugin.json,
        validates manifests, and loads enabled plugins dynamically into tool_registry.
        """
        if not os.path.exists(self.plugins_dir):
            os.makedirs(self.plugins_dir, exist_ok=True)
            log_structured(backend_log, "INFO", f"[PluginManager] Created plugins directory at '{self.plugins_dir}'")

        log_structured(backend_log, "INFO", f"[PluginManager] Discovering local plugins in '{self.plugins_dir}'...")
        discovered = []

        try:
            entries = os.listdir(self.plugins_dir)
        except Exception as e:
            log_structured(backend_log, "ERROR", f"[PluginManager] Error listing plugins directory: {str(e)}")
            return []

        for item in entries:
            folder_path = os.path.join(self.plugins_dir, item)
            if not os.path.isdir(folder_path):
                continue

            manifest_path = os.path.join(folder_path, "plugin.json")
            if not os.path.exists(manifest_path):
                continue

            valid, manifest, err = PluginValidator.validate_manifest_file(manifest_path)
            if not valid or not manifest:
                log_structured(
                    backend_log,
                    "WARNING",
                    f"[PluginManager] Skipping invalid plugin manifest at '{manifest_path}': {err}"
                )
                continue

            state = PluginState(
                plugin_id=manifest.id,
                manifest=manifest,
                status=PluginStatus.VALIDATED,
                plugin_dir=folder_path
            )

            # Load plugin
            PluginLifecycleManager.load_plugin(state)
            discovered.append(state)

        log_structured(
            backend_log,
            "INFO",
            f"[PluginManager] Plugin discovery completed. Total discovered & managed plugins: {len(discovered)}"
        )
        return discovered

    def get_all_plugins(self) -> List[PluginState]:
        return plugin_registry_instance.get_all_plugins()

    def get_plugin(self, plugin_id: str) -> Optional[PluginState]:
        return plugin_registry_instance.get_plugin(plugin_id)

    def enable_plugin(self, plugin_id: str) -> bool:
        return PluginLifecycleManager.enable_plugin(plugin_id)

    def disable_plugin(self, plugin_id: str) -> bool:
        return PluginLifecycleManager.disable_plugin(plugin_id)

    def reload_plugin(self, plugin_id: str) -> bool:
        return PluginLifecycleManager.reload_plugin(plugin_id)

    def health_check(self, plugin_id: str) -> bool:
        return PluginLifecycleManager.health_check_plugin(plugin_id)

plugin_manager = PluginManager()
