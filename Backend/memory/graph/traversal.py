from typing import List, Dict, Any, Optional, Set
from memory.models.graph import KnowledgeNode, KnowledgeEdge
from memory.storage.base import BaseGraphStorageProvider
from memory.storage.interfaces import InMemoryStorageProvider
from tools.telemetry import log_structured, backend_log


class GraphTraversalResult:
    def __init__(self, start_node_id: str, nodes: List[KnowledgeNode], edges: List[KnowledgeEdge]):
        self.start_node_id = start_node_id
        self.nodes = nodes
        self.edges = edges


class GraphTraversal:
    """
    Read-only graph traversal engine for 1-hop and 2-hop graph neighborhood lookups
    with built-in cycle detection, visited node tracking, and depth safety bounds.
    """

    def __init__(self, storage_provider: Optional[BaseGraphStorageProvider] = None):
        self.storage: BaseGraphStorageProvider = storage_provider or InMemoryStorageProvider()

    async def traverse_1hop(
        self,
        start_node_id: str,
        relationship_filter: Optional[str] = None
    ) -> GraphTraversalResult:
        """
        Executes a 1-hop graph neighborhood query from start_node_id.
        """
        start_node = await self.storage.get_node(start_node_id)
        if not start_node:
            return GraphTraversalResult(start_node_id, [], [])

        edges = await self.storage.get_edges(start_node_id, direction="both")
        
        retained_edges: List[KnowledgeEdge] = []
        neighbor_nodes: Dict[str, KnowledgeNode] = {start_node.node_id: start_node}
        visited: Set[str] = {start_node.node_id}

        for edge in edges:
            if relationship_filter and edge.relationship.upper() != relationship_filter.upper():
                continue

            neighbor_id = edge.target_node_id if edge.source_node_id == start_node_id else edge.source_node_id
            
            # Avoid self-loops
            if neighbor_id == start_node_id:
                continue

            if neighbor_id not in visited:
                node = await self.storage.get_node(neighbor_id)
                if node:
                    visited.add(neighbor_id)
                    neighbor_nodes[neighbor_id] = node
                    retained_edges.append(edge)

        return GraphTraversalResult(
            start_node_id=start_node_id,
            nodes=list(neighbor_nodes.values()),
            edges=retained_edges
        )

    async def traverse_2hop(
        self,
        start_node_id: str,
        relationship_filter: Optional[str] = None
    ) -> GraphTraversalResult:
        """
        Executes a 2-hop cycle-safe graph traversal query from start_node_id.
        """
        # Step 1: Perform 1-hop traversal
        hop1_res = await self.traverse_1hop(start_node_id, relationship_filter=relationship_filter)
        
        all_nodes: Dict[str, KnowledgeNode] = {n.node_id: n for n in hop1_res.nodes}
        all_edges: Dict[str, KnowledgeEdge] = {e.edge_id: e for e in hop1_res.edges}
        visited: Set[str] = set(all_nodes.keys())

        # Step 2: Traverse 2nd hop from each 1-hop neighbor
        hop1_neighbor_ids = [n.node_id for n in hop1_res.nodes if n.node_id != start_node_id]

        for n_id in hop1_neighbor_ids:
            edges = await self.storage.get_edges(n_id, direction="both")
            for edge in edges:
                if relationship_filter and edge.relationship.upper() != relationship_filter.upper():
                    continue

                neighbor_id = edge.target_node_id if edge.source_node_id == n_id else edge.source_node_id
                
                # Prevent cycles & self-loops
                if neighbor_id not in visited and neighbor_id != start_node_id:
                    node = await self.storage.get_node(neighbor_id)
                    if node:
                        visited.add(neighbor_id)
                        all_nodes[neighbor_id] = node
                        all_edges[edge.edge_id] = edge

        log_structured(
            backend_log,
            "INFO",
            f"[GraphTraversal] 2-hop traversal from '{start_node_id}' returned {len(all_nodes)} nodes and {len(all_edges)} edges"
        )

        return GraphTraversalResult(
            start_node_id=start_node_id,
            nodes=list(all_nodes.values()),
            edges=list(all_edges.values())
        )
