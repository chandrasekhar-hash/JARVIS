from typing import Optional, List, Dict, Any
from brain.event_bus import event_bus
from memory.models.graph import KnowledgeNode, KnowledgeEdge
from memory.storage.base import BaseGraphStorageProvider
from memory.storage.graph_provider import SQLiteGraphStorageProvider

from memory.storage.interfaces import InMemoryStorageProvider
from tools.telemetry import log_structured, backend_log


class GraphEngine:
    """
    Manages Knowledge Graph mutation operations (create, update, merge, delete) and
    enforces structural consistency across nodes and edges.
    """

    def __init__(self, storage_provider: Optional[BaseGraphStorageProvider] = None):
        self.storage: BaseGraphStorageProvider = storage_provider or InMemoryStorageProvider()

    async def add_node(self, node: KnowledgeNode) -> bool:
        """Stores a KnowledgeNode and emits KnowledgeNodeCreated event."""
        success = await self.storage.add_node(node)
        if success:
            event_bus.emit("KnowledgeNodeCreated", node_id=node.node_id, label=node.label, type=node.type)
            log_structured(backend_log, "INFO", f"[GraphEngine] Created node '{node.label}' ({node.node_id})")
        return success

    async def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        """Retrieves a KnowledgeNode by ID."""
        return await self.storage.get_node(node_id)

    async def add_edge(self, edge: KnowledgeEdge) -> bool:
        """
        Stores a directional KnowledgeEdge with self-loop and duplicate prevention.
        """
        # 1. Prevent Self-Loops
        if edge.source_node_id == edge.target_node_id:
            log_structured(backend_log, "WARNING", f"[GraphEngine] Prevented self-loop edge for node '{edge.source_node_id}'")
            return False

        # 2. Check node existence
        src_node = await self.storage.get_node(edge.source_node_id)
        tgt_node = await self.storage.get_node(edge.target_node_id)
        if not src_node or not tgt_node:
            log_structured(backend_log, "WARNING", f"[GraphEngine] Missing endpoint node for edge '{edge.edge_id}'")
            return False

        success = await self.storage.add_edge(edge)
        if success:
            event_bus.emit(
                "KnowledgeEdgeCreated",
                edge_id=edge.edge_id,
                source_id=edge.source_node_id,
                target_id=edge.target_node_id,
                relationship=edge.relationship
            )
            log_structured(backend_log, "INFO", f"[GraphEngine] Created edge '{src_node.label}' --[{edge.relationship}]--> '{tgt_node.label}'")
        return success

    async def merge_nodes(self, source_node_id: str, target_node_id: str) -> bool:
        """
        Merges source_node_id into target_node_id:
        1. Merges properties into target node.
        2. Redirects all edges from source_node_id to target_node_id.
        3. Deletes source_node_id.
        """
        if source_node_id == target_node_id:
            return False

        src_node = await self.storage.get_node(source_node_id)
        tgt_node = await self.storage.get_node(target_node_id)
        if not src_node or not tgt_node:
            return False

        # 1. Merge Properties
        merged_props = dict(src_node.properties)
        merged_props.update(tgt_node.properties)
        tgt_node.properties = merged_props
        await self.storage.add_node(tgt_node)

        # 2. Redirect Edges
        edges = await self.storage.get_edges(source_node_id, direction="both")
        for edge in edges:
            await self.storage.delete_edge(edge.edge_id)
            new_src = target_node_id if edge.source_node_id == source_node_id else edge.source_node_id
            new_tgt = target_node_id if edge.target_node_id == source_node_id else edge.target_node_id
            
            # Avoid self-loops after merge
            if new_src != new_tgt:
                new_edge = KnowledgeEdge(
                    edge_id=f"edge_redirected_{edge.edge_id}",
                    source_node_id=new_src,
                    target_node_id=new_tgt,
                    relationship=edge.relationship,
                    weight=edge.weight,
                    confidence=edge.confidence,
                    created_at=edge.created_at
                )
                await self.storage.add_edge(new_edge)

        # 3. Delete Source Node
        await self.storage.delete_node(source_node_id)

        event_bus.emit(
            "KnowledgeNodeMerged",
            source_id=source_node_id,
            target_id=target_node_id,
            target_label=tgt_node.label
        )
        event_bus.emit("KnowledgeGraphUpdated", action="node_merged")
        log_structured(backend_log, "INFO", f"[GraphEngine] Merged node '{source_node_id}' into '{target_node_id}'")
        return True

    async def delete_node(self, node_id: str) -> bool:
        """Deletes a node and cleans up associated edges."""
        success = await self.storage.delete_node(node_id)
        if success:
            event_bus.emit("KnowledgeGraphUpdated", action="node_deleted")
        return success


# Singleton instance of GraphEngine
graph_engine = GraphEngine()
