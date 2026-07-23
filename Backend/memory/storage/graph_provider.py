import os
import sqlite3
import json
import time
import asyncio
from typing import List, Optional, Dict, Any
from memory.models.graph import KnowledgeNode, KnowledgeEdge
from memory.storage.base import BaseGraphStorageProvider


class SQLiteGraphStorageProvider(BaseGraphStorageProvider):
    """
    Production SQLite implementation of BaseGraphStorageProvider supporting Knowledge Graph node
    and edge persistence across process restarts.
    """

    def __init__(self, db_path: str = "logs/jarvis_memory.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Nodes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_nodes (
                    node_id TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    type TEXT NOT NULL,
                    properties_json TEXT,
                    created_at REAL
                )
            """)
            # Edges table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_edges (
                    edge_id TEXT PRIMARY KEY,
                    source_node_id TEXT NOT NULL,
                    target_node_id TEXT NOT NULL,
                    relationship TEXT NOT NULL,
                    weight REAL,
                    confidence REAL,
                    created_at REAL,
                    FOREIGN KEY(source_node_id) REFERENCES knowledge_nodes(node_id) ON DELETE CASCADE,
                    FOREIGN KEY(target_node_id) REFERENCES knowledge_nodes(node_id) ON DELETE CASCADE
                )
            """)
            conn.commit()

    async def _run_sync(self, func, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    # ── Node Operations ───────────────────────────────────────────────────────

    def _add_node_sync(self, node: KnowledgeNode) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO knowledge_nodes (node_id, label, type, properties_json, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (node.node_id, node.label, node.type, json.dumps(node.properties), node.created_at))
            conn.commit()
            return True

    async def add_node(self, node: KnowledgeNode) -> bool:
        return await self._run_sync(self._add_node_sync, node)

    def _get_node_sync(self, node_id: str) -> Optional[KnowledgeNode]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM knowledge_nodes WHERE node_id = ?", (node_id,))
            row = cursor.fetchone()
            if not row:
                return None
            props = json.loads(row["properties_json"]) if row["properties_json"] else {}
            return KnowledgeNode(
                node_id=row["node_id"],
                label=row["label"],
                type=row["type"],
                properties=props,
                created_at=row["created_at"]
            )

    async def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        return await self._run_sync(self._get_node_sync, node_id)

    def _delete_node_sync(self, node_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM knowledge_edges WHERE source_node_id = ? OR target_node_id = ?", (node_id, node_id))
            cursor.execute("DELETE FROM knowledge_nodes WHERE node_id = ?", (node_id,))
            conn.commit()
            return cursor.rowcount > 0

    async def delete_node(self, node_id: str) -> bool:
        return await self._run_sync(self._delete_node_sync, node_id)

    # ── Edge Operations ───────────────────────────────────────────────────────

    def _add_edge_sync(self, edge: KnowledgeEdge) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO knowledge_edges (edge_id, source_node_id, target_node_id, relationship, weight, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (edge.edge_id, edge.source_node_id, edge.target_node_id, edge.relationship, edge.weight, edge.confidence, edge.created_at))
            conn.commit()
            return True

    async def add_edge(self, edge: KnowledgeEdge) -> bool:
        return await self._run_sync(self._add_edge_sync, edge)

    def _get_edges_sync(self, node_id: str, direction: str = "both") -> List[KnowledgeEdge]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if direction == "outbound":
                cursor.execute("SELECT * FROM knowledge_edges WHERE source_node_id = ?", (node_id,))
            elif direction == "inbound":
                cursor.execute("SELECT * FROM knowledge_edges WHERE target_node_id = ?", (node_id,))
            else:
                cursor.execute("SELECT * FROM knowledge_edges WHERE source_node_id = ? OR target_node_id = ?", (node_id, node_id))
            
            rows = cursor.fetchall()
            edges = []
            for r in rows:
                edges.append(KnowledgeEdge(
                    edge_id=r["edge_id"],
                    source_node_id=r["source_node_id"],
                    target_node_id=r["target_node_id"],
                    relationship=r["relationship"],
                    weight=r["weight"],
                    confidence=r["confidence"] if "confidence" in r.keys() and r["confidence"] is not None else 1.0,
                    created_at=r["created_at"]
                ))
            return edges


    async def get_edges(self, node_id: str, direction: str = "both") -> List[KnowledgeEdge]:
        return await self._run_sync(self._get_edges_sync, node_id, direction)

    def _delete_edge_sync(self, edge_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM knowledge_edges WHERE edge_id = ?", (edge_id,))
            conn.commit()
            return cursor.rowcount > 0

    async def delete_edge(self, edge_id: str) -> bool:
        return await self._run_sync(self._delete_edge_sync, edge_id)
