from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from memory.models.memory import Memory, MemoryChunk
from memory.models.graph import KnowledgeNode, KnowledgeEdge
from memory.models.query import MemorySummary


class BaseMemoryStorageProvider(ABC):
    """Abstract Base Class for relational & metadata memory storage providers."""

    @abstractmethod
    async def store_memory(self, memory: Memory) -> str:
        """Stores a new memory. Returns the memory_id."""
        pass

    @abstractmethod
    async def get_memory(self, memory_id: str) -> Optional[Memory]:
        """Retrieves a memory by its unique ID."""
        pass

    @abstractmethod
    async def update_memory(self, memory_id: str, updates: Dict[str, Any]) -> Optional[Memory]:
        """Updates metadata/content fields of an existing memory."""
        pass

    @abstractmethod
    async def delete_memory(self, memory_id: str) -> bool:
        """Permanently deletes a memory by ID."""
        pass

    @abstractmethod
    async def archive_memory(self, memory_id: str) -> bool:
        """Archives a memory (sets state to archived/decayed)."""
        pass

    @abstractmethod
    async def list_memories(
        self,
        memory_type: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Memory]:
        """Lists memories with optional filtering by type or tag."""
        pass

    @abstractmethod
    async def get_summary(self) -> MemorySummary:
        """Returns overall memory subsystem telemetry and counts."""
        pass


class BaseVectorStorageProvider(ABC):
    """Abstract Base Class for vector embedding storage and distance providers."""

    @abstractmethod
    async def add_vector(self, chunk: MemoryChunk) -> bool:
        """Adds or updates a vector embedding entry for a MemoryChunk."""
        pass

    @abstractmethod
    async def get_vector(self, chunk_id: str) -> Optional[List[float]]:
        """Retrieves vector embedding for a given chunk_id."""
        pass

    @abstractmethod
    async def search_vectors(self, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Performs vector similarity search against the index."""
        pass

    @abstractmethod
    async def delete_vector(self, chunk_id: str) -> bool:
        """Deletes a vector entry by chunk_id."""
        pass


class BaseGraphStorageProvider(ABC):
    """Abstract Base Class for Knowledge Graph node & edge relationship providers."""

    @abstractmethod
    async def add_node(self, node: KnowledgeNode) -> bool:
        """Adds or updates a Knowledge Node."""
        pass

    @abstractmethod
    async def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        """Retrieves a Knowledge Node by ID."""
        pass

    @abstractmethod
    async def delete_node(self, node_id: str) -> bool:
        """Deletes a Knowledge Node and its associated edges."""
        pass

    @abstractmethod
    async def add_edge(self, edge: KnowledgeEdge) -> bool:
        """Adds a Knowledge Edge connecting two nodes."""
        pass

    @abstractmethod
    async def get_edges(self, node_id: str, direction: str = "both") -> List[KnowledgeEdge]:
        """Retrieves edges connected to a node (inbound, outbound, or both)."""
        pass

    @abstractmethod
    async def delete_edge(self, edge_id: str) -> bool:
        """Deletes a Knowledge Edge by ID."""
        pass
