import os
import sys
import importlib.util
import inspect
from typing import Tuple, List, Dict, Any, Optional
from plugins.plugin_models import PluginState, PluginStatus
from tools.registry import registry as tool_registry
from tools.telemetry import log_structured, backend_log

class PluginLoader:
    """
    Dynamically loads Python plugin entrypoints from Backend/plugins_installed/<id>/<entry>
    using importlib.util and registers exported plugin tools into tool_registry.
    Ensures complete exception isolation so plugin errors never crash the backend.
    """

    @staticmethod
    def load_plugin_module(state: PluginState) -> Tuple[bool, List[str], Optional[str]]:
        entry_path = os.path.join(state.plugin_dir, state.manifest.entry)
        module_name = f"plugins_installed.{state.plugin_id}.{os.path.splitext(state.manifest.entry)[0]}"
        
        try:
            spec = importlib.util.spec_from_file_location(module_name, entry_path)
            if spec is None or spec.loader is None:
                return False, [], f"Could not create spec for plugin module: {entry_path}"
                
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            registered_tools = []
            
            # 1. Check if plugin defines an explicit setup_plugin(registry) function
            if hasattr(module, "setup_plugin") and callable(module.setup_plugin):
                try:
                    tools_added = module.setup_plugin(tool_registry)
                    if isinstance(tools_added, list):
                        registered_tools.extend(tools_added)
                except Exception as e:
                    return False, [], f"Error in plugin setup_plugin(): {str(e)}"
            
            # 2. Check functions in module exported with _plugin_tool_meta attribute
            for name, func in inspect.getmembers(module, inspect.isfunction):
                if hasattr(func, "_plugin_tool_meta"):
                    meta = getattr(func, "_plugin_tool_meta")
                    tool_name = meta.get("name") or f"plugin_{state.plugin_id}_{name}"
                    tool_desc = meta.get("description") or f"Tool provided by plugin {state.manifest.name}"
                    tool_params = meta.get("parameters") or {"type": "object", "properties": {}}
                    safety = meta.get("safety_level") or "safe"
                    
                    tool_registry.register(
                        name=tool_name,
                        description=tool_desc,
                        parameters=tool_params,
                        safety_level=safety
                    )(func)
                    registered_tools.append(tool_name)

            log_structured(
                backend_log,
                "INFO",
                f"[PluginLoader] Successfully loaded plugin '{state.plugin_id}' with tools: {registered_tools}"
            )
            return True, registered_tools, None

        except Exception as e:
            err_msg = f"Failed to load plugin module '{state.plugin_id}': {str(e)}"
            log_structured(backend_log, "ERROR", f"[PluginLoader] {err_msg}")
            return False, [], err_msg

loader = PluginLoader()
