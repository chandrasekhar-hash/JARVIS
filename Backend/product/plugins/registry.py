"""
Product 1.4 Plugin & Skills Registry Component.
"""
import logging
from typing import Dict, List, Optional, Any
from .models import PluginState, PluginStatus, SkillDefinition, CommandDefinition

logger = logging.getLogger("JARVIS_PluginRegistry")


class PluginRegistry:
    """
    Thread-safe registry managing registered plugin states.
    """

    def __init__(self):
        self._plugins: Dict[str, PluginState] = {}

    def register_plugin(self, state: PluginState) -> bool:
        """Registers or updates a plugin state in the registry."""
        self._plugins[state.plugin_id] = state
        logger.info(f"[PluginRegistry] Registered plugin '{state.plugin_id}' with status '{state.status.value}'.")
        return True

    def unregister_plugin(self, plugin_id: str) -> bool:
        """Removes a plugin from the registry."""
        if plugin_id in self._plugins:
            del self._plugins[plugin_id]
            logger.info(f"[PluginRegistry] Unregistered plugin '{plugin_id}'.")
            return True
        return False

    def get_plugin(self, plugin_id: str) -> Optional[PluginState]:
        """Retrieves plugin state by identifier."""
        return self._plugins.get(plugin_id)

    def get_all_plugins(self) -> List[PluginState]:
        """Returns all registered plugin states."""
        return list(self._plugins.values())

    def get_plugins_by_status(self, status: PluginStatus) -> List[PluginState]:
        """Filters plugins by status."""
        return [s for s in self._plugins.values() if s.status == status]

    def get_plugins_by_category(self, category: str) -> List[PluginState]:
        """Filters plugins by manifest category."""
        return [s for s in self._plugins.values() if s.manifest.category == category]


class SkillsRegistry:
    """
    Registry for managing executable skills exposed by plugins.
    Binds skills dynamically into core tool registry.
    """

    def __init__(self, core_tool_registry: Optional[Any] = None):
        self._skills: Dict[str, SkillDefinition] = {}
        self.core_tool_registry = core_tool_registry

    def register_skill(
        self,
        skill_id: str,
        plugin_id: str,
        name: str,
        description: str,
        handler: Any,
        intent_patterns: Optional[List[str]] = None,
        parameters_schema: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Registers a new skill definition."""
        full_skill_id = f"{plugin_id}.{skill_id}" if not skill_id.startswith(f"{plugin_id}.") else skill_id

        skill_def = SkillDefinition(
            skill_id=full_skill_id,
            plugin_id=plugin_id,
            name=name,
            description=description,
            handler=handler,
            intent_patterns=intent_patterns or [],
            parameters_schema=parameters_schema or {},
        )
        self._skills[full_skill_id] = skill_def

        # Optionally bind to core tool_registry
        if self.core_tool_registry is not None and hasattr(self.core_tool_registry, "register_tool"):
            try:
                self.core_tool_registry.register_tool(
                    name=full_skill_id,
                    description=description,
                    func=handler,
                    category="plugin_skill",
                )
            except Exception as e:
                logger.warning(f"[SkillsRegistry] Core tool registration warning for '{full_skill_id}': {e}")

        logger.info(f"[SkillsRegistry] Registered skill '{full_skill_id}' for plugin '{plugin_id}'.")
        return True

    def unregister_skills_for_plugin(self, plugin_id: str) -> List[str]:
        """Unregisters all skills belonging to a specific plugin."""
        removed_ids = []
        skill_ids = list(self._skills.keys())

        for s_id in skill_ids:
            if self._skills[s_id].plugin_id == plugin_id:
                del self._skills[s_id]
                removed_ids.append(s_id)
                # Unregister from core tool registry if present
                if self.core_tool_registry is not None and hasattr(self.core_tool_registry, "tools"):
                    self.core_tool_registry.tools.pop(s_id, None)

        logger.info(f"[SkillsRegistry] Unregistered {len(removed_ids)} skills for plugin '{plugin_id}'.")
        return removed_ids

    def get_skill(self, skill_id: str) -> Optional[SkillDefinition]:
        """Retrieves a skill definition by ID."""
        return self._skills.get(skill_id)

    def get_all_skills(self) -> List[SkillDefinition]:
        """Returns all registered skills."""
        return list(self._skills.values())


class CommandRegistry:
    """
    Registry for direct shortcut commands exposed by plugins.
    """

    def __init__(self):
        self._commands: Dict[str, CommandDefinition] = {}

    def register_command(
        self,
        plugin_id: str,
        trigger_keyword: str,
        handler: Any,
        description: str = "",
    ) -> bool:
        """Registers a direct command shortcut."""
        cmd_def = CommandDefinition(
            trigger_keyword=trigger_keyword,
            plugin_id=plugin_id,
            handler=handler,
            description=description,
        )
        self._commands[trigger_keyword] = cmd_def
        logger.info(f"[CommandRegistry] Registered command '{trigger_keyword}' for plugin '{plugin_id}'.")
        return True

    def unregister_commands_for_plugin(self, plugin_id: str) -> List[str]:
        """Unregisters all commands belonging to a specific plugin."""
        removed = []
        kw_list = list(self._commands.keys())
        for kw in kw_list:
            if self._commands[kw].plugin_id == plugin_id:
                del self._commands[kw]
                removed.append(kw)
        return removed

    def get_command(self, trigger_keyword: str) -> Optional[CommandDefinition]:
        return self._commands.get(trigger_keyword)


# Global instances
plugin_registry_instance = PluginRegistry()
skills_registry_instance = SkillsRegistry()
command_registry_instance = CommandRegistry()
