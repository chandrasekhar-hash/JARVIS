import inspect
import logging
import asyncio
from typing import Dict, Any, Optional, Callable
from enum import Enum

logger = logging.getLogger("JARVIS_PluginLifecycle")


class ExtendedPluginStatus(str, Enum):
    INSTALLING = "INSTALLING"
    INSTALLED = "INSTALLED"
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"
    UPDATING = "UPDATING"
    UNINSTALLED = "UNINSTALLED"


class PluginLifecycleManager:
    """
    Manages 6-state lifecycle (INSTALLING -> INSTALLED -> ENABLED -> DISABLED -> UPDATING -> UNINSTALLED)
    and executes lifecycle hook callbacks (on_install, on_enable, on_disable, on_upgrade, on_uninstall).
    """

    def __init__(self):
        # plugin_id -> ExtendedPluginStatus
        self.plugin_states: Dict[str, ExtendedPluginStatus] = {}

    def set_status(self, plugin_id: str, status: ExtendedPluginStatus):
        old_status = self.plugin_states.get(plugin_id, "NONE")
        self.plugin_states[plugin_id] = status
        logger.info(f"Plugin '{plugin_id}' lifecycle transition: {old_status} -> {status.value}")

    async def run_hook(self, plugin_id: str, hook_name: str, hook_func: Optional[Callable] = None):
        logger.info(f"Executing lifecycle hook '{hook_name}' for plugin '{plugin_id}'...")
        if hook_func:
            try:
                if inspect.iscoroutinefunction(hook_func):
                    await hook_func()
                else:
                    hook_func()
            except Exception as e:
                logger.error(f"Error executing hook '{hook_name}' for plugin '{plugin_id}': {e}")

    async def install_plugin(self, plugin_id: str, hook_func: Optional[Callable] = None) -> bool:
        self.set_status(plugin_id, ExtendedPluginStatus.INSTALLING)
        await self.run_hook(plugin_id, "on_install", hook_func)
        self.set_status(plugin_id, ExtendedPluginStatus.INSTALLED)
        return True

    async def enable_plugin(self, plugin_id: str, hook_func: Optional[Callable] = None) -> bool:
        await self.run_hook(plugin_id, "on_enable", hook_func)
        self.set_status(plugin_id, ExtendedPluginStatus.ENABLED)
        return True

    async def disable_plugin(self, plugin_id: str, hook_func: Optional[Callable] = None) -> bool:
        await self.run_hook(plugin_id, "on_disable", hook_func)
        self.set_status(plugin_id, ExtendedPluginStatus.DISABLED)
        return True

    async def upgrade_plugin(self, plugin_id: str, hook_func: Optional[Callable] = None) -> bool:
        self.set_status(plugin_id, ExtendedPluginStatus.UPDATING)
        await self.run_hook(plugin_id, "on_upgrade", hook_func)
        self.set_status(plugin_id, ExtendedPluginStatus.ENABLED)
        return True

    async def uninstall_plugin(self, plugin_id: str, hook_func: Optional[Callable] = None) -> bool:
        await self.run_hook(plugin_id, "on_uninstall", hook_func)
        self.set_status(plugin_id, ExtendedPluginStatus.UNINSTALLED)
        return True


plugin_lifecycle = PluginLifecycleManager()
