from typing import Dict, Type
import os
import config
from ai.providers.provider import AIProvider
from tools.telemetry import log_structured, backend_log

class ProviderRegistry:
    def __init__(self):
        self._provider_classes: Dict[str, Type[AIProvider]] = {}
        self._instances: Dict[str, AIProvider] = {}
        self._initialized_names = set()

    def register(self, name: str, provider_class: Type[AIProvider]) -> None:
        """Registers a provider class under a name."""
        cleaned_name = name.lower().strip()
        self._provider_classes[cleaned_name] = provider_class
        # Clear cached instance if any to force recreation if re-registered
        self._instances.pop(cleaned_name, None)
        self._initialized_names.discard(cleaned_name)
        log_structured(backend_log, "INFO", f"[AI] Provider '{name}' registered in registry")

    @property
    def active_provider_name(self) -> str:
        # Resolve active provider name dynamically from env or configuration
        prov = os.getenv("ACTIVE_PROVIDER", getattr(config, "ACTIVE_PROVIDER", "groq"))
        return prov.lower().strip()

    def get_active_provider(self) -> AIProvider:
        provider_name = self.active_provider_name
        if provider_name not in self._provider_classes:
            log_structured(
                backend_log, 
                "WARNING", 
                f"[AI] Active provider '{provider_name}' not found. Falling back to 'groq'"
            )
            provider_name = "groq"

        if provider_name not in self._provider_classes:
            raise RuntimeError("No valid AI providers registered in registry.")

        # Instantiate lazily
        if provider_name not in self._instances:
            self._instances[provider_name] = self._provider_classes[provider_name]()

        provider = self._instances[provider_name]

        # Initialize lazily
        if provider_name not in self._initialized_names:
            log_structured(backend_log, "INFO", f"[AI] Active Provider: {provider_name.capitalize()}")
            provider.initialize()
            self._initialized_names.add(provider_name)

        return provider

    def get_registered_providers(self) -> Dict[str, Type[AIProvider]]:
        """Returns all registered provider classes."""
        return self._provider_classes.copy()

    def get_provider(self, name: str) -> AIProvider:
        """Retrieves or instantiates a registered provider dynamically by name."""
        cleaned_name = name.lower().strip()
        if cleaned_name not in self._provider_classes:
            raise ValueError(f"Provider '{name}' is not registered.")
            
        if cleaned_name not in self._instances:
            self._instances[cleaned_name] = self._provider_classes[cleaned_name]()
            
        provider = self._instances[cleaned_name]
        
        if cleaned_name not in self._initialized_names:
            log_structured(backend_log, "INFO", f"[AI] Active Provider: {cleaned_name.capitalize()}")
            provider.initialize()
            self._initialized_names.add(cleaned_name)
            
        return provider

provider_registry = ProviderRegistry()

# Register all providers here
from ai.providers.groq_provider import GroqProvider
from ai.providers.gemini_provider import GeminiProvider
from ai.providers.openrouter_provider import OpenRouterProvider
from ai.providers.cerebras_provider import CerebrasProvider

provider_registry.register("groq", GroqProvider)
provider_registry.register("gemini", GeminiProvider)
provider_registry.register("openrouter", OpenRouterProvider)
provider_registry.register("cerebras", CerebrasProvider)
