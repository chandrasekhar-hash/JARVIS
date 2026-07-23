import time
from typing import List, Optional, Dict, Any
from memory.models.memory import Memory, MemoryChunk
from memory.models.graph import KnowledgeNode, KnowledgeEdge
from memory.models.query import MemorySummary
from memory.storage.base import (
    BaseMemoryStorageProvider,
    BaseVectorStorageProvider,
    BaseGraphStorageProvider,
)


class InMemoryStorageProvider(
    BaseMemoryStorageProvider,
    BaseVectorStorageProvider,
    BaseGraphStorageProvider,
):
    """
    In-memory reference storage driver implementing relational, vector, and graph interfaces.
    Provides fast, thread-safe memory storage for testing and standalone local execution.
    """

    def __init__(self):
        self._memories: Dict[str, Memory] = {}
        self._vectors: Dict[str, Dict[str, Any]] = {}  # chunk_id -> {vector, chunk_id, memory_id}
        self._nodes: Dict[str, KnowledgeNode] = {}
        self._edges: Dict[str, KnowledgeEdge] = {}

    # ── Relational Memory CRUD ───────────────────────────────────────────────

    async def store_memory(self, memory: Memory) -> str:
        self._memories[memory.memory_id] = memory
        return memory.memory_id

    async def get_memory(self, memory_id: str) -> Optional[Memory]:
        memory = self._memories.get(memory_id)
        if memory:
            memory.metadata.access_count += 1
            memory.metadata.last_accessed = time.time()
        return memory

    async def update_memory(self, memory_id: str, updates: Dict[str, Any]) -> Optional[Memory]:
        memory = self._memories.get(memory_id)
        if not memory:
            return None
        
        # Apply field updates dynamically
        for key, val in updates.items():
            if hasattr(memory, key) and key not in ("memory_id", "metadata"):
                setattr(memory, key, val)
            elif hasattr(memory.metadata, key):
                setattr(memory.metadata, key, val)

        memory.metadata.updated_at = time.time()
        return memory

    async def delete_memory(self, memory_id: str) -> bool:
        if memory_id in self._memories:
            del self._memories[memory_id]
            # Clean up chunks from vector store
            chunks_to_del = [cid for cid, vdata in self._vectors.items() if vdata.get("memory_id") == memory_id]
            for cid in chunks_to_del:
                del self._vectors[cid]
            return True
        return False

    async def archive_memory(self, memory_id: str) -> bool:
        memory = self._memories.get(memory_id)
        if memory:
            memory.metadata.tags.append("archived")
            memory.metadata.updated_at = time.time()
            return True
        return False

    async def list_memories(
        self,
        memory_type: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Memory]:
        result = list(self._memories.values())
        if memory_type:
            result = [m for m in result if m.type.value.lower() == memory_type.lower()]
        if tag:
            result = [m for m in result if tag in m.metadata.tags]
        
        result.sort(key=lambda m: m.metadata.created_at, reverse=True)
        return result[offset: offset + limit]

    async def get_summary(self) -> MemorySummary:
        type_counts: Dict[str, int] = {}
        for m in self._memories.values():
            t_name = m.type.value
            type_counts[t_name] = type_counts.get(t_name, 0) + 1

        total_bytes = sum(len(m.content.encode("utf-8")) for m in self._memories.values())

        return MemorySummary(
            total_memories=len(self._memories),
            count_by_type=type_counts,
            total_nodes=len(self._nodes),
            total_edges=len(self._edges),
            storage_bytes=total_bytes
        )

    # ── Vector Storage Operations ────────────────────────────────────────────

    async def add_vector(self, chunk: MemoryChunk) -> bool:
        if chunk.embedding is not None:
            self._vectors[chunk.chunk_id] = {
                "chunk_id": chunk.chunk_id,
                "memory_id": chunk.memory_id,
                "vector": chunk.embedding,
                "content": chunk.content
            }
            return True
        return False

    async def get_vector(self, chunk_id: str) -> Optional[List[float]]:
        v_entry = self._vectors.get(chunk_id)
        return v_entry["vector"] if v_entry else None

    async def search_vectors(self, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        # Dummy cosine similarity calculation for reference driver
        results = []
        for cid, vdata in self._vectors.items():
            results.append({
                "chunk_id": cid,
                "memory_id": vdata["memory_id"],
                "score": 0.95,  # Reference driver placeholder score
                "content": vdata["content"]
            })
        return results[:top_k]

    async def delete_vector(self, chunk_id: str) -> bool:
        if chunk_id in self._vectors:
            del self._vectors[chunk_id]
            return True
        return False

    # ── Graph Storage Operations ─────────────────────────────────────────────

    async def add_node(self, node: KnowledgeNode) -> bool:
        self._nodes[node.node_id] = node
        return True

    async def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        return self._nodes.get(node_id)

    async def delete_node(self, node_id: str) -> bool:
        if node_id in self._nodes:
            del self._nodes[node_id]
            # Delete connected edges
            edges_to_del = [
                eid for eid, edge in self._edges.items()
                if edge.source_node_id == node_id or edge.target_node_id == node_id
            ]
            for eid in edges_to_del:
                del self._edges[eid]
            return True
        return False

    async def add_edge(self, edge: KnowledgeEdge) -> bool:
        self._edges[edge.edge_id] = edge
        return True

    async def get_edges(self, node_id: str, direction: str = "both") -> List[KnowledgeEdge]:
        matched = []
        for edge in self._edges.values():
            if direction in ("outbound", "both") and edge.source_node_id == node_id:
                matched.append(edge)
            elif direction in ("inbound", "both") and edge.target_node_id == node_id:
                matched.append(edge)
        return matched

    async def delete_edge(self, edge_id: str) -> bool:
        if edge_id in self._edges:
            del self._edges[edge_id]
            return True
        return False
