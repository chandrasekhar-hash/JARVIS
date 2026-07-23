import os
from typing import Optional
from memory.storage.base import (
    BaseMemoryStorageProvider,
    BaseVectorStorageProvider,
    BaseGraphStorageProvider,
)
from memory.storage.interfaces import InMemoryStorageProvider
from memory.storage.sqlite_provider import SQLiteMemoryStorageProvider
from memory.storage.vector_provider import SQLiteVectorStorageProvider
from memory.storage.graph_provider import SQLiteGraphStorageProvider
from tools.telemetry import log_structured, backend_log


class StorageProviderFactory:
    """
    Factory for instantiating memory, vector, and graph storage providers dynamically based on
    configuration settings while enforcing provider independence for MemoryManager.
    """

    @staticmethod
    def get_memory_provider(provider_type: Optional[str] = None, db_path: str = "logs/jarvis_memory.db") -> BaseMemoryStorageProvider:
        p_type = (provider_type or os.getenv("MEMORY_STORAGE_PROVIDER", "sqlite")).lower().strip()
        if p_type == "in_memory":
            log_structured(backend_log, "INFO", "[StorageFactory] Instantiating InMemoryStorageProvider")
            return InMemoryStorageProvider()
        else:
            log_structured(backend_log, "INFO", f"[StorageFactory] Instantiating SQLiteMemoryStorageProvider at '{db_path}'")
            return SQLiteMemoryStorageProvider(db_path=db_path)

    @staticmethod
    def get_vector_provider(provider_type: Optional[str] = None, db_path: str = "logs/jarvis_memory.db") -> BaseVectorStorageProvider:
        p_type = (provider_type or os.getenv("VECTOR_STORAGE_PROVIDER", "sqlite")).lower().strip()
        if p_type == "in_memory":
            return InMemoryStorageProvider()
        else:
            return SQLiteVectorStorageProvider(db_path=db_path)

    @staticmethod
    def get_graph_provider(provider_type: Optional[str] = None, db_path: str = "logs/jarvis_memory.db") -> BaseGraphStorageProvider:
        p_type = (provider_type or os.getenv("GRAPH_STORAGE_PROVIDER", "sqlite")).lower().strip()
        if p_type == "in_memory":
            return InMemoryStorageProvider()
        else:
            return SQLiteGraphStorageProvider(db_path=db_path)


def get_storage_provider(provider_type: Optional[str] = None) -> BaseMemoryStorageProvider:
    """Helper function returning the configured relational memory storage provider."""
    return StorageProviderFactory.get_memory_provider(provider_type)
