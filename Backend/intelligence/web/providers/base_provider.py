"""
Base Search Provider Abstraction for J.A.R.V.I.S. I2.2 V1 Web Search Foundation.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseSearchProvider(ABC):
    """Abstract interface for all web search providers."""

    @abstractmethod
    def get_provider_name(self) -> str:
        """Returns the identifier name of the search provider."""
        pass

    @abstractmethod
    async def search(self, query: str, max_results: int = 10, **kwargs) -> List[Dict[str, Any]]:
        """
        Executes search against the provider.
        Returns raw result items containing at minimum: title, url, snippet, and optional metadata.
        """
        pass
