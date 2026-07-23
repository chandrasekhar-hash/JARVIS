import time
import uuid
from typing import List, Optional, Tuple, Dict, Any
from memory.models.graph import KnowledgeNode, KnowledgeEdge


class RelationshipBuilder:
    """
    Infers directional relationship edges between KnowledgeNodes based on semantic heuristics
    and observation patterns.
    """

    @staticmethod
    def infer_relationships(nodes: List[KnowledgeNode], context_text: str = "") -> List[KnowledgeEdge]:
        """
        Infers directional relationships between nodes extracted from the same context.
        """
        edges: List[KnowledgeEdge] = []
        if len(nodes) < 2:
            return edges

        now = time.time()
        context_lower = context_text.lower()

        # Map node types to lists of nodes
        node_map: Dict[str, List[KnowledgeNode]] = {}
        for n in nodes:
            node_map.setdefault(n.type.lower(), []).append(n)

        # 1. Person --PREFERS--> Topic / Application
        persons = node_map.get("person", [])
        apps = node_map.get("application", [])
        topics = node_map.get("topic", [])
        projects = node_map.get("project", [])
        files = node_map.get("file", [])

        for p in persons:
            for app in apps:
                if p.node_id != app.node_id:
                    edges.append(
                        KnowledgeEdge(
                            edge_id=f"edge_{p.node_id}_{app.node_id}_prefers",
                            source_node_id=p.node_id,
                            target_node_id=app.node_id,
                            relationship="PREFERS",
                            weight=0.9,
                            confidence=0.85,
                            created_at=now
                        )
                    )

            for top in topics:
                if p.node_id != top.node_id:
                    rel_type = "PREFERS" if "prefer" in context_lower or "like" in context_lower else "RELATED_TO"
                    edges.append(
                        KnowledgeEdge(
                            edge_id=f"edge_{p.node_id}_{top.node_id}_{rel_type.lower()}",
                            source_node_id=p.node_id,
                            target_node_id=top.node_id,
                            relationship=rel_type,
                            weight=0.8,
                            confidence=0.80,
                            created_at=now
                        )
                    )

        # 2. Project --USES--> Topic / Application
        for prj in projects:
            for top in topics:
                if prj.node_id != top.node_id:
                    edges.append(
                        KnowledgeEdge(
                            edge_id=f"edge_{prj.node_id}_{top.node_id}_uses",
                            source_node_id=prj.node_id,
                            target_node_id=top.node_id,
                            relationship="USES",
                            weight=0.85,
                            confidence=0.90,
                            created_at=now
                        )
                    )

        # 3. File --PART_OF--> Project
        for f in files:
            for prj in projects:
                if f.node_id != prj.node_id:
                    edges.append(
                        KnowledgeEdge(
                            edge_id=f"edge_{f.node_id}_{prj.node_id}_part_of",
                            source_node_id=f.node_id,
                            target_node_id=prj.node_id,
                            relationship="PART_OF",
                            weight=1.0,
                            confidence=0.95,
                            created_at=now
                        )
                    )

        # 4. Fallback: Node_i --RELATED_TO--> Node_j for remaining distinct pairs
        if not edges and len(nodes) >= 2:
            n1, n2 = nodes[0], nodes[1]
            if n1.node_id != n2.node_id:
                edges.append(
                    KnowledgeEdge(
                        edge_id=f"edge_{n1.node_id}_{n2.node_id}_related_to",
                        source_node_id=n1.node_id,
                        target_node_id=n2.node_id,
                        relationship="RELATED_TO",
                        weight=0.5,
                        confidence=0.70,
                        created_at=now
                    )
                )

        return edges
