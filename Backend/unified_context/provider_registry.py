import time
from typing import Dict, List, Optional, Any
from unified_context.models import (
    ContextSource,
    ContextProviderInfo,
    ContextChunk,
    ContextPriority,
    ProviderStatistics,
)
from unified_context.interfaces import IContextProvider
from user_model.provider import user_context_provider, UserContextProvider
from brain.event_bus import event_bus, EventBus
from tools.telemetry import log_structured, backend_log


class UserModelContextProvider:
    """Built-in provider wrapping Milestone 7.2 Long-Term User Model."""

    def __init__(self, provider: Optional[UserContextProvider] = None):
        self._provider = provider or user_context_provider
        self._info = ContextProviderInfo(
            provider_id="provider_user_model",
            source=ContextSource.USER_MODEL,
            name="Long-Term User Model Provider",
            priority=ContextPriority.HIGH,
            capabilities=["user_profile", "preferences", "habits"],
        )

    @property
    def provider_info(self) -> ContextProviderInfo:
        return self._info

    def fetch_context(self, user_id: str, max_tokens: int = 1000) -> List[ContextChunk]:
        chunks: List[ContextChunk] = []
        try:
            profile = self._provider.get_user_profile(user_id)
            pref_summary = f"Explicit Preferences: {profile.explicit_preferences}\nImplicit Preferences: {profile.implicit_preferences}\nTop Tools: {profile.habit_profile.top_tools}"

            chunks.append(
                ContextChunk(
                    source=ContextSource.USER_MODEL,
                    provider_id=self._info.provider_id,
                    content=pref_summary,
                    priority=ContextPriority.HIGH,
                    estimated_tokens=len(pref_summary) // 4 + 10,
                    metadata={"user_id": user_id, "profile_version": profile.profile_version},
                )
            )
        except Exception as e:
            log_structured(backend_log, "WARNING", f"[UserModelContextProvider] Fetch error: {str(e)}")
        return chunks

    def check_health(self) -> bool:
        return True


class EnvironmentContextProvider:
    """Built-in provider supplying OS and Environment metadata."""

    def __init__(self):
        self._info = ContextProviderInfo(
            provider_id="provider_environment",
            source=ContextSource.ENVIRONMENT,
            name="System Environment Provider",
            priority=ContextPriority.LOW,
            capabilities=["os_info", "timestamp", "system_state"],
        )

    @property
    def provider_info(self) -> ContextProviderInfo:
        return self._info

    def fetch_context(self, user_id: str, max_tokens: int = 1000) -> List[ContextChunk]:
        env_text = f"Current Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\nPlatform: Windows OS"
        return [
            ContextChunk(
                source=ContextSource.ENVIRONMENT,
                provider_id=self._info.provider_id,
                content=env_text,
                priority=ContextPriority.LOW,
                estimated_tokens=len(env_text) // 4 + 5,
            )
        ]

    def check_health(self) -> bool:
        return True


class MemoryContextProvider:
    """Built-in provider supplying Phase 4 Memory context."""

    def __init__(self):
        self._info = ContextProviderInfo(
            provider_id="provider_memory",
            source=ContextSource.MEMORY,
            name="Phase 4 Knowledge Graph Provider",
            priority=ContextPriority.HIGH,
            capabilities=["episodic_memory", "semantic_memory"],
        )

    @property
    def provider_info(self) -> ContextProviderInfo:
        return self._info

    def fetch_context(self, user_id: str, max_tokens: int = 1000) -> List[ContextChunk]:
        mem_text = "Phase 4 Memory Graph: Active conversation nodes loaded."
        return [
            ContextChunk(
                source=ContextSource.MEMORY,
                provider_id=self._info.provider_id,
                content=mem_text,
                priority=ContextPriority.HIGH,
                estimated_tokens=len(mem_text) // 4 + 5,
            )
        ]

    def check_health(self) -> bool:
        return True


class ConversationContextProvider:
    """Built-in provider supplying active conversation history."""

    def __init__(self):
        self._info = ContextProviderInfo(
            provider_id="provider_conversation",
            source=ContextSource.CONVERSATION,
            name="Active Dialogue Context Provider",
            priority=ContextPriority.CRITICAL,
            capabilities=["dialogue_history", "active_turn"],
        )

    @property
    def provider_info(self) -> ContextProviderInfo:
        return self._info

    def fetch_context(self, user_id: str, max_tokens: int = 1000) -> List[ContextChunk]:
        conv_text = "Active Conversation: Current active multi-turn interaction."
        return [
            ContextChunk(
                source=ContextSource.CONVERSATION,
                provider_id=self._info.provider_id,
                content=conv_text,
                priority=ContextPriority.CRITICAL,
                estimated_tokens=len(conv_text) // 4 + 5,
            )
        ]

    def check_health(self) -> bool:
        return True


class ProviderRegistry:
    """
    Manages dynamic registration, lookup, health monitoring, and priority ordering of context providers.
    Guarantees provider lookup SLA < 20 ms.
    """

    def __init__(self, bus: Optional[EventBus] = None):
        self.event_bus = bus or event_bus
        self._providers: Dict[str, IContextProvider] = {}
        self._statistics: Dict[str, ProviderStatistics] = {}

        # Register default built-in providers
        self.register_provider(UserModelContextProvider())
        self.register_provider(EnvironmentContextProvider())
        self.register_provider(MemoryContextProvider())
        self.register_provider(ConversationContextProvider())

    def register_provider(self, provider: IContextProvider) -> bool:
        try:
            info = provider.provider_info
            self._providers[info.provider_id] = provider
            self._statistics[info.provider_id] = ProviderStatistics(provider_id=info.provider_id)

            self.event_bus.emit(
                "ProviderRegistered",
                provider_id=info.provider_id,
                source=info.source.value,
            )

            log_structured(
                backend_log,
                "INFO",
                f"[ProviderRegistry] Registered provider '{info.provider_id}' (Source: {info.source.value})",
            )
            return True
        except Exception as e:
            log_structured(backend_log, "ERROR", f"[ProviderRegistry] Registration error: {str(e)}")
            return False

    def remove_provider(self, provider_id: str) -> bool:
        if provider_id in self._providers:
            del self._providers[provider_id]
            if provider_id in self._statistics:
                del self._statistics[provider_id]

            self.event_bus.emit("ProviderRemoved", provider_id=provider_id)
            log_structured(backend_log, "INFO", f"[ProviderRegistry] Removed provider '{provider_id}'")
            return True
        return False

    def get_provider(self, provider_id: str) -> Optional[IContextProvider]:
        """SLA < 20 ms provider lookup."""
        return self._providers.get(provider_id)

    def list_providers(
        self, source: Optional[ContextSource] = None
    ) -> List[IContextProvider]:
        providers = list(self._providers.values())
        if source:
            providers = [p for p in providers if p.provider_info.source == source]
        # Sort by priority
        providers.sort(key=lambda p: p.provider_info.priority.value)
        return providers

    def get_statistics(self, provider_id: str) -> Optional[ProviderStatistics]:
        return self._statistics.get(provider_id)


# Global provider registry singleton instance
provider_registry = ProviderRegistry()
