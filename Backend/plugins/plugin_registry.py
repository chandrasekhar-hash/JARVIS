from typing import Dict, List, Optional
from plugins.plugin_models import PluginState, PluginStatus
from tools.telemetry import log_structured, backend_log

class PluginRegistry:
    """
    Central registry tracking installed plugin states, metadata, manifests,
    statuses, and registered tools.
    """

    def __init__(self):
        self._plugins: Dict[str, PluginState] = {}

    def register_plugin(self, state: PluginState) -> None:
        self._plugins[state.plugin_id] = state
        log_structured(backend_log, "INFO", f"[PluginRegistry] Registered plugin state '{state.plugin_id}' ({state.status.value})")

    def get_plugin(self, plugin_id: str) -> Optional[PluginState]:
        return self._plugins.get(plugin_id)

    def get_all_plugins(self) -> List[PluginState]:
        return list(self._plugins.values())

    def unregister_plugin(self, plugin_id: str) -> Optional[PluginState]:
        return self._plugins.pop(plugin_id, None)

plugin_registry_instance = PluginRegistry()
