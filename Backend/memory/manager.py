from typing import List, Optional, Dict, Any
from brain.event_bus import event_bus
from memory.models.memory import Memory
from memory.models.query import MemorySummary
from memory.storage.base import BaseMemoryStorageProvider
from memory.storage.provider_factory import StorageProviderFactory
from tools.telemetry import log_structured, backend_log


class MemoryManager:
    """
    Central facade and single entry point for all Memory operations in Phase 4.
    
    Guarantees provider independence by interacting strictly through abstract
    storage interfaces (BaseMemoryStorageProvider). Neither Brain nor context
    providers ever access raw storage drivers directly.
    """

    def __init__(self, storage_provider: Optional[BaseMemoryStorageProvider] = None):
        self._storage: BaseMemoryStorageProvider = storage_provider or StorageProviderFactory.get_memory_provider()
        log_structured(backend_log, "INFO", f"[MemoryManager] Initialized with provider: {self._storage.__class__.__name__}")


    def set_storage_provider(self, provider: BaseMemoryStorageProvider) -> None:
        """Dynamically swaps the underlying storage provider."""
        self._storage = provider
        log_structured(backend_log, "INFO", f"[MemoryManager] Swapped storage provider to: {provider.__class__.__name__}")

    async def store_memory(self, memory: Memory) -> str:
        """Stores a new memory, emits MemoryCreated event, and returns memory_id."""
        mem_id = await self._storage.store_memory(memory)
        event_bus.emit("MemoryCreated", memory_id=mem_id, memory_type=memory.type.value, title=memory.title)
        log_structured(backend_log, "INFO", f"[MemoryManager] Stored memory '{mem_id}' ({memory.type.value})")
        return mem_id

    async def get_memory(self, memory_id: str) -> Optional[Memory]:
        """Retrieves a memory by its unique memory_id."""
        return await self._storage.get_memory(memory_id)

    async def update_memory(self, memory_id: str, updates: Dict[str, Any]) -> Optional[Memory]:
        """Updates fields of an existing memory and emits MemoryUpdated event."""
        updated = await self._storage.update_memory(memory_id, updates)
        if updated:
            event_bus.emit("MemoryUpdated", memory_id=memory_id, updated_fields=list(updates.keys()))
            log_structured(backend_log, "INFO", f"[MemoryManager] Updated memory '{memory_id}'")
        return updated

    async def delete_memory(self, memory_id: str) -> bool:
        """Permanently deletes a memory by memory_id and emits MemoryForgotten event."""
        success = await self._storage.delete_memory(memory_id)
        if success:
            event_bus.emit("MemoryForgotten", memory_id=memory_id, mode="delete")
            log_structured(backend_log, "INFO", f"[MemoryManager] Deleted memory '{memory_id}'")
        return success

    async def archive_memory(self, memory_id: str) -> bool:
        """Archives a memory and emits MemoryArchived event."""
        success = await self._storage.archive_memory(memory_id)
        if success:
            event_bus.emit("MemoryArchived", memory_id=memory_id)
            log_structured(backend_log, "INFO", f"[MemoryManager] Archived memory '{memory_id}'")
        return success

    async def forget_memory(self, tag: Optional[str] = None, memory_type: Optional[str] = None) -> int:
        """
        Selective forgetting operation: deletes all memories matching specified tag or type.
        Emits MemoryForgotten event for each purged memory and returns count.
        """
        memories = await self._storage.list_memories(memory_type=memory_type, tag=tag, limit=1000)
        purged_count = 0
        for mem in memories:
            if await self._storage.delete_memory(mem.memory_id):
                purged_count += 1
                event_bus.emit("MemoryForgotten", memory_id=mem.memory_id, mode="selective_forgetting")
        
        log_structured(backend_log, "INFO", f"[MemoryManager] Selective forgetting purged {purged_count} memories (tag={tag}, type={memory_type})")
        return purged_count

    async def list_memories(
        self,
        memory_type: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Memory]:
        """Lists stored memories with optional filtering."""
        return await self._storage.list_memories(memory_type=memory_type, tag=tag, limit=limit, offset=offset)

    async def get_summary(self) -> MemorySummary:
        """Returns overall memory subsystem telemetry and counts."""
        return await self._storage.get_summary()


# Singleton instance of MemoryManager
memory_manager = MemoryManager()
