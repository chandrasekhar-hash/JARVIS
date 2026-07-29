"""
J.A.R.V.I.S. Product Layer Phase P1.2 (Memory & Personalization) Package Initialization.
Exports memory models, enums, interfaces, store repositories, hybrid search engine, and public memory engine.
"""
from .memory_models import (
    Memory,
    MemoryCategory,
    MemoryType,
    MemoryStatus,
    ImportanceLevel,
    RetentionPolicy,
    MemoryTag,
    MemoryLink,
    MemoryCollection,
    MemorySettings,
    PersonalizationProfile,
    MemorySearchResult,
)
from .memory_interfaces import (
    IMemoryRepository,
    IPersonalizationRepository,
    IMemorySettingsRepository,
    IMemorySearchEngine,
    IMemorySummarizer,
    IMemoryContextBuilder,
)
from .memory_migration import MemorySchemaMigration
from .memory_store import SQLiteMemoryRepository
from .memory_index import MemoryIndex
from .memory_search import MemorySearchEngine
from .memory_summarizer import MemorySummarizer
from .memory_context import MemoryContextBuilder
from .memory_settings import MemorySettingsManager
from .memory_engine import MemoryEngine, memory_engine

__all__ = [
    "Memory",
    "MemoryCategory",
    "MemoryType",
    "MemoryStatus",
    "ImportanceLevel",
    "RetentionPolicy",
    "MemoryTag",
    "MemoryLink",
    "MemoryCollection",
    "MemorySettings",
    "PersonalizationProfile",
    "MemorySearchResult",
    "IMemoryRepository",
    "IPersonalizationRepository",
    "IMemorySettingsRepository",
    "IMemorySearchEngine",
    "IMemorySummarizer",
    "IMemoryContextBuilder",
    "MemorySchemaMigration",
    "SQLiteMemoryRepository",
    "MemoryIndex",
    "MemorySearchEngine",
    "MemorySummarizer",
    "MemoryContextBuilder",
    "MemorySettingsManager",
    "MemoryEngine",
    "memory_engine",
]
