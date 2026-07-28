import os
import time
import sys
from typing import Tuple, Optional
from plugins.plugin_models import PluginState, PluginStatus
from plugins.plugin_loader import PluginLoader
from plugins.plugin_registry import plugin_registry_instance
from tools.registry import registry as tool_registry
from tools.telemetry import log_structured, backend_log

class PluginLifecycleManager:
    """
    Manages state transitions and operations for local plugins:
    LOAD, UNLOAD, ENABLE, DISABLE, RELOAD, and HEALTH_CHECK.
    """

    @staticmethod
    def load_plugin(state: PluginState) -> bool:
        if not state.manifest.enabled:
            state.status = PluginStatus.DISABLED
            plugin_registry_instance.register_plugin(state)
            return True

        success, tools, err = PluginLoader.load_plugin_module(state)
        if success:
            state.status = PluginStatus.RUNNING
            state.loaded_at = time.time()
            state.registered_tools = tools
            state.health_ok = True
            state.error_message = None
        else:
            state.status = PluginStatus.FAILED
            state.health_ok = False
            state.error_message = err

        plugin_registry_instance.register_plugin(state)
        return success

    @staticmethod
    def unload_plugin(plugin_id: str) -> bool:
        state = plugin_registry_instance.get_plugin(plugin_id)
        if not state:
            return False

        # Unregister plugin tools from tool_registry
        for tool_name in state.registered_tools:
            tool_registry.tools.pop(tool_name, None)
            
        state.registered_tools = []
        state.status = PluginStatus.UNLOADED
        
        # Remove module from sys.modules
        module_name = f"plugins_installed.{state.plugin_id}.{os.path.splitext(state.manifest.entry)[0]}" if hasattr(os.path, "splitext") else ""
        if module_name in sys.modules:
            sys.modules.pop(module_name, None)
            
        log_structured(backend_log, "INFO", f"[PluginLifecycle] Unloaded plugin '{plugin_id}'")
        return True

    @staticmethod
    def disable_plugin(plugin_id: str) -> bool:
        state = plugin_registry_instance.get_plugin(plugin_id)
        if not state:
            return False

        # Unregister tools from tool_registry
        for tool_name in state.registered_tools:
            tool_registry.tools.pop(tool_name, None)

        state.manifest.enabled = False
        state.status = PluginStatus.DISABLED
        log_structured(backend_log, "INFO", f"[PluginLifecycle] Disabled plugin '{plugin_id}'")
        return True

    @staticmethod
    def enable_plugin(plugin_id: str) -> bool:
        state = plugin_registry_instance.get_plugin(plugin_id)
        if not state:
            return False

        state.manifest.enabled = True
        return PluginLifecycleManager.load_plugin(state)

    @staticmethod
    def reload_plugin(plugin_id: str) -> bool:
        state = plugin_registry_instance.get_plugin(plugin_id)
        if not state:
            return False

        PluginLifecycleManager.unload_plugin(plugin_id)
        return PluginLifecycleManager.load_plugin(state)

    @staticmethod
    def health_check_plugin(plugin_id: str) -> bool:
        state = plugin_registry_instance.get_plugin(plugin_id)
        if not state:
            return False

        entry_path = f"{state.plugin_dir}/{state.manifest.entry}"
        import os
        is_ok = os.path.exists(entry_path) and state.status in [PluginStatus.RUNNING, PluginStatus.LOADED, PluginStatus.DISABLED]
        state.health_ok = is_ok
        return is_ok

lifecycle_manager = PluginLifecycleManager()
