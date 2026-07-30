"""
Product 1.4 ProductPluginManager Master Orchestrator.
"""
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from .models import PluginState, PluginStatus, PluginManifest
from .validator import PluginValidator
from .registry import (
    plugin_registry_instance,
    skills_registry_instance,
    command_registry_instance,
    PluginRegistry,
    SkillsRegistry,
    CommandRegistry,
)
from .permissions import permission_engine, PluginPermissionEngine
from .config_engine import config_engine_instance, PluginConfigEngine
from .api_context import PluginAPIContext
from .lifecycle import PluginLifecycleManager
from .isolation import PluginIsolationGuard

logger = logging.getLogger("JARVIS_ProductPluginManager")


class ProductPluginManager:
    """
    Production-grade Master Orchestrator for Product 1.4 Plugin & Skills Framework.
    Discovers, validates, resolves dependencies, initializes, activates, and executes plugins safely.
    """

    def __init__(
        self,
        plugins_dir: str = "backend/plugins_installed",
        core_tool_registry: Optional[Any] = None,
        event_bus: Optional[Any] = None,
        memory_engine: Optional[Any] = None,
        preference_manager: Optional[Any] = None,
    ):
        self.plugins_dir = plugins_dir
        self.core_tool_registry = core_tool_registry
        self.event_bus = event_bus
        self.memory_engine = memory_engine
        self.preference_manager = preference_manager

        self.registry: PluginRegistry = plugin_registry_instance
        self.skills_registry: SkillsRegistry = skills_registry_instance
        self.command_registry: CommandRegistry = command_registry_instance
        self.permissions: PluginPermissionEngine = permission_engine
        self.config_engine: PluginConfigEngine = config_engine_instance

        if core_tool_registry is not None:
            self.skills_registry.core_tool_registry = core_tool_registry
        if preference_manager is not None:
            self.config_engine.preference_manager = preference_manager

        self._modules: Dict[str, Any] = {}

    def discover_and_load_plugins(self, plugins_dir: Optional[str] = None) -> List[PluginState]:
        """
        Scans directory for plugin packages, validates manifests, resolves dependency DAG,
        and initializes enabled plugins.
        """
        search_dir = plugins_dir or self.plugins_dir

        # Expand search path candidates if relative
        candidates = [
            search_dir,
            "backend/plugins_installed",
            "plugins_installed",
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "plugins_installed"),
        ]
        target_dir = search_dir
        for c in candidates:
            if os.path.exists(c):
                target_dir = c
                break

        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)

        logger.info(f"[ProductPluginManager] Discovering plugins in '{target_dir}'...")

        try:
            entries = os.listdir(target_dir)
        except Exception as e:
            logger.error(f"[ProductPluginManager] Error reading plugin directory: {str(e)}")
            return []

        discovered_states: List[PluginState] = []

        for item in entries:
            folder_path = os.path.join(target_dir, item)
            if not os.path.isdir(folder_path):
                continue

            manifest_path = os.path.join(folder_path, "plugin.json")
            if not os.path.exists(manifest_path):
                continue

            valid, manifest, err = PluginValidator.validate_manifest_file(manifest_path)
            if not valid or manifest is None:
                logger.warning(f"[ProductPluginManager] Skipping invalid plugin at '{folder_path}': {err}")
                continue

            state = PluginState(
                plugin_id=manifest.id,
                manifest=manifest,
                status=PluginStatus.VALIDATED,
                plugin_dir=folder_path,
            )
            discovered_states.append(state)

        if not discovered_states:
            logger.info("[ProductPluginManager] No valid plugin packages discovered.")
            return []

        # Dependency Resolution DAG
        ok_dag, sorted_ids, dag_err = PluginValidator.resolve_dependencies_dag(discovered_states)
        if not ok_dag:
            logger.error(f"[ProductPluginManager] Dependency resolution failed: {dag_err}")
            return []

        state_map = {s.plugin_id: s for s in discovered_states}
        loaded_states: List[PluginState] = []

        for p_id in sorted_ids:
            state = state_map[p_id]
            self.registry.register_plugin(state)

            if not state.manifest.enabled_by_default:
                state.status = PluginStatus.DISABLED
                logger.info(f"[ProductPluginManager] Plugin '{p_id}' disabled by default manifest setting.")
                continue

            # Create PluginAPIContext for plugin
            context = PluginAPIContext(
                plugin_id=state.plugin_id,
                manifest=state.manifest,
                skills_registry=self.skills_registry,
                event_dispatcher=self.event_bus,
                command_registry=self.command_registry,
                memory_engine=self.memory_engine,
            )

            # Initialize and Activate
            success = PluginLifecycleManager.load_and_initialize_plugin(state, context)
            if success:
                # Retrieve loaded module from sys.modules
                mod_name = f"jarvis_plugin_{state.plugin_id}"
                import sys
                module = sys.modules.get(mod_name)
                if module:
                    self._modules[state.plugin_id] = module

                PluginLifecycleManager.activate_plugin(state, module=module)
                loaded_states.append(state)

        logger.info(f"[ProductPluginManager] Plugin discovery and loading complete. Managed plugins: {len(self.registry.get_all_plugins())}")
        return self.registry.get_all_plugins()

    def get_plugin(self, plugin_id: str) -> Optional[PluginState]:
        return self.registry.get_plugin(plugin_id)

    def get_all_plugins(self) -> List[PluginState]:
        return self.registry.get_all_plugins()

    def enable_plugin(self, plugin_id: str) -> bool:
        """Enables and activates a disabled plugin."""
        state = self.registry.get_plugin(plugin_id)
        if not state:
            return False

        if state.status == PluginStatus.ACTIVATED:
            return True

        state.manifest.enabled_by_default = True
        context = PluginAPIContext(
            plugin_id=state.plugin_id,
            manifest=state.manifest,
            skills_registry=self.skills_registry,
            event_dispatcher=self.event_bus,
            command_registry=self.command_registry,
            memory_engine=self.memory_engine,
        )

        ok = PluginLifecycleManager.load_and_initialize_plugin(state, context)
        if ok:
            import sys
            mod_name = f"jarvis_plugin_{state.plugin_id}"
            module = sys.modules.get(mod_name)
            if module:
                self._modules[state.plugin_id] = module
            return PluginLifecycleManager.activate_plugin(state, module=module)
        return False

    def disable_plugin(self, plugin_id: str) -> bool:
        """Disables and deactivates a running plugin."""
        state = self.registry.get_plugin(plugin_id)
        if not state:
            return False

        module = self._modules.get(plugin_id)
        PluginLifecycleManager.deactivate_plugin(state, module=module)
        self.skills_registry.unregister_skills_for_plugin(plugin_id)
        self.command_registry.unregister_commands_for_plugin(plugin_id)
        state.status = PluginStatus.DISABLED
        return True

    def reload_plugin(self, plugin_id: str) -> bool:
        """Unloads and reloads a plugin cleanly."""
        state = self.registry.get_plugin(plugin_id)
        if not state:
            return False

        self.unload_plugin(plugin_id)
        return self.enable_plugin(plugin_id)

    def unload_plugin(self, plugin_id: str) -> bool:
        """Completely unloads a plugin and purges its registered skills/commands/modules."""
        state = self.registry.get_plugin(plugin_id)
        if not state:
            return False

        module = self._modules.pop(plugin_id, None)
        self.skills_registry.unregister_skills_for_plugin(plugin_id)
        self.command_registry.unregister_commands_for_plugin(plugin_id)
        return PluginLifecycleManager.unload_plugin(state, module=module)

    async def execute_skill(
        self,
        plugin_id: str,
        skill_id: str,
        *args: Any,
        **kwargs: Any,
    ) -> Tuple[bool, Any, Optional[str]]:
        """
        Safely executes a registered plugin skill through isolation guard and permission engine.
        """
        state = self.registry.get_plugin(plugin_id)
        if not state:
            return False, None, f"Plugin '{plugin_id}' not found."

        full_skill_id = f"{plugin_id}.{skill_id}" if not skill_id.startswith(f"{plugin_id}.") else skill_id
        skill = self.skills_registry.get_skill(full_skill_id)
        if not skill or skill.handler is None:
            return False, None, f"Skill '{full_skill_id}' not found or has no handler."

        # Execute through PluginIsolationGuard
        return await PluginIsolationGuard.execute_async(state, skill.handler, *args, **kwargs)

    def get_plugin_health(self) -> Dict[str, Any]:
        """Returns health telemetry for all managed plugins."""
        all_plugins = self.registry.get_all_plugins()
        return {
            "total_plugins": len(all_plugins),
            "active_plugins": len([p for p in all_plugins if p.status == PluginStatus.ACTIVATED]),
            "failed_plugins": len([p for p in all_plugins if p.status == PluginStatus.FAILED]),
            "disabled_plugins": len([p for p in all_plugins if p.status == PluginStatus.DISABLED]),
            "total_skills": len(self.skills_registry.get_all_skills()),
        }


# Global singleton instance
plugin_manager_instance = ProductPluginManager()
