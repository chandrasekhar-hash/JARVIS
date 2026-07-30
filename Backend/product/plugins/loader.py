"""
Product 1.4 Dynamic Plugin Loader and Module Isolator.
"""
import os
import sys
import gc
import logging
import importlib.util
from typing import Tuple, Optional, Any, Dict
from .models import PluginState

logger = logging.getLogger("JARVIS_PluginLoader")


class PluginLoader:
    """
    Dynamically loads and unloads Python plugin modules from disk cleanly.
    """

    @staticmethod
    def load_plugin_module(state: PluginState) -> Tuple[bool, Optional[Any], Optional[str]]:
        """
        Loads the Python module entry point specified in state.manifest.entry_point.
        Returns:
            (success, module_instance, error_message)
        """
        entry_file = state.manifest.entry_point
        entry_path = os.path.join(state.plugin_dir, entry_file)

        if not os.path.exists(entry_path):
            err = f"Plugin entry point file not found at '{entry_path}'"
            logger.error(f"[PluginLoader] {err}")
            return False, None, err

        module_name = f"jarvis_plugin_{state.plugin_id}"

        try:
            spec = importlib.util.spec_from_file_location(module_name, entry_path)
            if spec is None or spec.loader is None:
                err = f"Failed to create spec for module at '{entry_path}'"
                logger.error(f"[PluginLoader] {err}")
                return False, None, err

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            logger.info(f"[PluginLoader] Successfully imported module '{module_name}' for plugin '{state.plugin_id}'")
            return True, module, None
        except Exception as e:
            err = f"Exception while executing plugin module '{entry_file}': {str(e)}"
            logger.error(f"[PluginLoader] {err}", exc_info=True)
            # Cleanup on failure
            if module_name in sys.modules:
                sys.modules.pop(module_name, None)
            return False, None, err

    @staticmethod
    def unload_plugin_module(plugin_id: str) -> bool:
        """
        Unloads imported plugin submodules from sys.modules and forces garbage collection.
        """
        module_name = f"jarvis_plugin_{plugin_id}"
        to_remove = [k for k in sys.modules if k == module_name or k.startswith(f"{module_name}.")]

        for mod_key in to_remove:
            sys.modules.pop(mod_key, None)

        gc.collect()
        logger.info(f"[PluginLoader] Unloaded {len(to_remove)} submodules for plugin '{plugin_id}'.")
        return True
