"""
Product 1.4 Plugin API Context Contract & Implementation.
"""
from abc import ABC, abstractmethod
import logging
from typing import Dict, Any, Optional, Callable, List, Awaitable
from .models import PluginManifest
from .permissions import permission_engine
from .config_engine import config_engine_instance


class IPluginAPIContext(ABC):
    """
    Public immutable API Contract exposed to plugins.
    """

    @abstractmethod
    def register_skill(
        self,
        skill_id: str,
        name: str,
        description: str,
        handler: Callable[..., Any],
        intent_patterns: Optional[List[str]] = None,
        parameters_schema: Optional[Dict[str, Any]] = None,
    ) -> bool:
        pass

    @abstractmethod
    def register_event(
        self,
        event_name: str,
        handler: Callable[[Dict[str, Any]], Awaitable[None]],
    ) -> bool:
        pass

    @abstractmethod
    def register_command(
        self,
        trigger_keyword: str,
        handler: Callable[[str], Any],
        description: str = "",
    ) -> bool:
        pass

    @abstractmethod
    def get_setting(self, key: str, default: Any = None) -> Any:
        pass

    @abstractmethod
    def set_setting(self, key: str, value: Any) -> bool:
        pass

    @abstractmethod
    def get_memory(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    def set_memory(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        pass

    @abstractmethod
    def logger(self) -> logging.Logger:
        pass

    @abstractmethod
    def emit_event(self, event_name: str, payload: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def check_permission(self, scope: str) -> bool:
        pass


class PluginAPIContext(IPluginAPIContext):
    """
    Concrete implementation of PluginAPIContext provided to each plugin at initialization.
    """

    def __init__(
        self,
        plugin_id: str,
        manifest: PluginManifest,
        skills_registry: Any,
        event_dispatcher: Any,
        command_registry: Any,
        memory_engine: Optional[Any] = None,
    ):
        self.plugin_id = plugin_id
        self.manifest = manifest
        self._skills_registry = skills_registry
        self._event_dispatcher = event_dispatcher
        self._command_registry = command_registry
        self._memory_engine = memory_engine
        self._logger = logging.getLogger(f"JARVIS_Plugin_{plugin_id}")
        self._memory_store: Dict[str, Any] = {}

    def register_skill(
        self,
        skill_id: str,
        name: str,
        description: str,
        handler: Callable[..., Any],
        intent_patterns: Optional[List[str]] = None,
        parameters_schema: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Registers a executable skill into the Skills Framework."""
        if not self._skills_registry:
            return False
        return self._skills_registry.register_skill(
            skill_id=skill_id,
            plugin_id=self.plugin_id,
            name=name,
            description=description,
            handler=handler,
            intent_patterns=intent_patterns or [],
            parameters_schema=parameters_schema or {},
        )

    def register_event(
        self,
        event_name: str,
        handler: Callable[[Dict[str, Any]], Awaitable[None]],
    ) -> bool:
        """Subscribes an async listener to system or domain event bus."""
        if not self._event_dispatcher:
            return False
        return self._event_dispatcher.register_event_listener(
            plugin_id=self.plugin_id,
            event_name=event_name,
            handler=handler,
        )

    def register_command(
        self,
        trigger_keyword: str,
        handler: Callable[[str], Any],
        description: str = "",
    ) -> bool:
        """Registers a direct shortcut command into Intent Classifier."""
        if not self._command_registry:
            return False
        return self._command_registry.register_command(
            plugin_id=self.plugin_id,
            trigger_keyword=trigger_keyword,
            handler=handler,
            description=description,
        )

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Retrieves a namespaced configuration setting for this plugin."""
        return config_engine_instance.get_setting(
            plugin_id=self.plugin_id,
            manifest=self.manifest,
            key=key,
            default=default,
        )

    def set_setting(self, key: str, value: Any) -> bool:
        """Updates a namespaced configuration setting."""
        return config_engine_instance.set_setting(
            plugin_id=self.plugin_id,
            manifest=self.manifest,
            key=key,
            value=value,
        )

    def get_memory(self, key: str) -> Optional[Any]:
        """Reads plugin-scoped persistent key-value state from P1.2 Memory."""
        if self._memory_engine and hasattr(self._memory_engine, "get_plugin_memory"):
            return self._memory_engine.get_plugin_memory(self.plugin_id, key)
        return self._memory_store.get(key)

    def set_memory(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Writes plugin-scoped persistent key-value state to P1.2 Memory."""
        if self._memory_engine and hasattr(self._memory_engine, "set_plugin_memory"):
            return self._memory_engine.set_plugin_memory(self.plugin_id, key, value, ttl_seconds)
        self._memory_store[key] = value
        return True

    def logger(self) -> logging.Logger:
        """Returns a pre-configured structured logger bound to plugin_id."""
        return self._logger

    def emit_event(self, event_name: str, payload: Dict[str, Any]) -> None:
        """Emits a domain event onto the central EventBus."""
        if self._event_dispatcher and hasattr(self._event_dispatcher, "emit"):
            self._event_dispatcher.emit(event_name, payload)

    def check_permission(self, scope: str) -> bool:
        """Validates if plugin possesses active authorization for requested permission scope."""
        return permission_engine.check_permission(
            plugin_id=self.plugin_id,
            manifest=self.manifest,
            scope=scope,
            raise_on_denial=True,
        )
