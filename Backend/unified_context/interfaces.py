from typing import Protocol, List, Optional, Dict, Any
from unified_context.models import (
    ContextSource,
    ContextProviderInfo,
    ContextChunk,
    CognitiveContext,
)


class IContextProvider(Protocol):
    @property
    def provider_info(self) -> ContextProviderInfo:
        ...

    def fetch_context(self, user_id: str, max_tokens: int = 1000) -> List[ContextChunk]:
        ...

    def check_health(self) -> bool:
        ...


class IProviderRegistry(Protocol):
    def register_provider(self, provider: IContextProvider) -> bool:
        ...

    def remove_provider(self, provider_id: str) -> bool:
        ...

    def get_provider(self, provider_id: str) -> Optional[IContextProvider]:
        ...

    def list_providers(
        self, source: Optional[ContextSource] = None
    ) -> List[IContextProvider]:
        ...


class ITokenBudgeter(Protocol):
    def allocate_tokens(
        self, chunks: List[ContextChunk], max_budget: int = 4096
    ) -> List[ContextChunk]:
        ...


class IStateAssembler(Protocol):
    def collect_and_merge(
        self, providers: List[IContextProvider], user_id: str
    ) -> List[ContextChunk]:
        ...


class IUnifiedContextEngine(Protocol):
    async def assemble_context(
        self, user_id: str = "default_user", max_budget: int = 4096
    ) -> CognitiveContext:
        ...
