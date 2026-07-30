"""
Product 1.4 Plugin Lifecycle State Manager.
"""
import time
import logging
from typing import Tuple, Optional, Any
from .models import PluginState, PluginStatus
from .loader import PluginLoader
from .isolation import PluginIsolationGuard
from .permissions import permission_engine

logger = logging.getLogger("JARVIS_PluginLifecycleManager")


class PluginLifecycleManager:
    """
    State machine governing plugin state transitions:
    DISCOVERED -> VALIDATED -> RESOLVED -> REGISTERED -> INITIALIZED -> ACTIVATED -> DEACTIVATED -> UNLOADED
    """

    @staticmethod
    def load_and_initialize_plugin(
        state: PluginState,
        api_context: Any,
    ) -> bool:
        """
        Imports plugin module, runs on_initialize(context) hook, and sets state to INITIALIZED.
        """
        # Load Python module
        ok, module, err = PluginLoader.load_plugin_module(state)
        if not ok or module is None:
            state.status = PluginStatus.FAILED
            state.error_message = err or "Module load failed"
            return False

        state.status = PluginStatus.REGISTERED

        # Initialize permissions
        permission_engine.initialize_plugin_permissions(state.plugin_id, state.manifest)

        # Run on_initialize hook if present
        init_func = getattr(module, "on_initialize", None) or getattr(module, "initialize", None)
        if init_func and callable(init_func):
            success, _, err_msg = PluginIsolationGuard.execute_sync(state, init_func, api_context)
            if not success:
                state.status = PluginStatus.FAILED
                state.error_message = f"Initialization hook failed: {err_msg}"
                return False

        state.status = PluginStatus.INITIALIZED
        state.loaded_at = time.time()
        logger.info(f"[PluginLifecycle] Successfully initialized plugin '{state.plugin_id}'.")
        return True

    @staticmethod
    def activate_plugin(state: PluginState, module: Optional[Any] = None) -> bool:
        """
        Runs on_activate() hook and transitions state to ACTIVATED.
        """
        if state.status in (PluginStatus.FAILED, PluginStatus.UNLOADED):
            logger.warning(f"[PluginLifecycle] Cannot activate plugin '{state.plugin_id}' in state '{state.status.value}'.")
            return False

        if module is not None:
            act_func = getattr(module, "on_activate", None) or getattr(module, "activate", None)
            if act_func and callable(act_func):
                success, _, err_msg = PluginIsolationGuard.execute_sync(state, act_func)
                if not success:
                    logger.warning(f"[PluginLifecycle] Plugin '{state.plugin_id}' on_activate hook error: {err_msg}")

        state.status = PluginStatus.ACTIVATED
        state.health_ok = True
        logger.info(f"[PluginLifecycle] Successfully activated plugin '{state.plugin_id}'.")
        return True

    @staticmethod
    def deactivate_plugin(state: PluginState, module: Optional[Any] = None) -> bool:
        """
        Runs on_deactivate() hook and transitions state to DEACTIVATED.
        """
        if module is not None:
            deact_func = getattr(module, "on_deactivate", None) or getattr(module, "deactivate", None)
            if deact_func and callable(deact_func):
                PluginIsolationGuard.execute_sync(state, deact_func)

        state.status = PluginStatus.DEACTIVATED
        logger.info(f"[PluginLifecycle] Deactivated plugin '{state.plugin_id}'.")
        return True

    @staticmethod
    def unload_plugin(state: PluginState, module: Optional[Any] = None) -> bool:
        """
        Runs on_unload() hook, cleans up references, and unloads python submodules.
        """
        PluginLifecycleManager.deactivate_plugin(state, module=module)

        if module is not None:
            unload_func = getattr(module, "on_unload", None) or getattr(module, "unload", None)
            if unload_func and callable(unload_func):
                PluginIsolationGuard.execute_sync(state, unload_func)

        PluginLoader.unload_plugin_module(state.plugin_id)
        state.status = PluginStatus.UNLOADED
        state.registered_skills = []
        state.registered_commands = []
        state.registered_events = []
        logger.info(f"[PluginLifecycle] Unloaded plugin '{state.plugin_id}'.")
        return True
