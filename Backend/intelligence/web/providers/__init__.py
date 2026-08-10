"""
Search Providers Package.
"""
from intelligence.web.providers.base_provider import BaseSearchProvider
from intelligence.web.providers.duckduckgo_provider import DuckDuckGoSearchProvider

__all__ = ["BaseSearchProvider", "DuckDuckGoSearchProvider"]
