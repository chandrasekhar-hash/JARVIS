import os
import sqlite3
import json
import math
import asyncio
from typing import List, Optional, Dict, Any
from memory.models.memory import MemoryChunk
from memory.storage.base import BaseVectorStorageProvider


class SQLiteVectorStorageProvider(BaseVectorStorageProvider):
    """
    Production SQLite implementation of BaseVectorStorageProvider supporting vector embedding
    storage and cosine similarity distance search across process restarts.
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
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vector_embeddings (
                    chunk_id TEXT PRIMARY KEY,
                    memory_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    vector_json TEXT NOT NULL
                )
            """)
            conn.commit()

    async def _run_sync(self, func, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Computes cosine similarity score between two float vectors."""
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot_prod = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        return dot_prod / (norm1 * norm2)

    def _add_vector_sync(self, chunk: MemoryChunk) -> bool:
        if chunk.embedding is None:
            return False
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO vector_embeddings (chunk_id, memory_id, content, vector_json)
                VALUES (?, ?, ?, ?)
            """, (chunk.chunk_id, chunk.memory_id, chunk.content, json.dumps(chunk.embedding)))
            conn.commit()
            return True

    async def add_vector(self, chunk: MemoryChunk) -> bool:
        return await self._run_sync(self._add_vector_sync, chunk)

    def _get_vector_sync(self, chunk_id: str) -> Optional[List[float]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT vector_json FROM vector_embeddings WHERE chunk_id = ?", (chunk_id,))
            row = cursor.fetchone()
            if row and row["vector_json"]:
                return json.loads(row["vector_json"])
            return None

    async def get_vector(self, chunk_id: str) -> Optional[List[float]]:
        return await self._run_sync(self._get_vector_sync, chunk_id)

    def _search_vectors_sync(self, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT chunk_id, memory_id, content, vector_json FROM vector_embeddings")
            rows = cursor.fetchall()
            
            scored_results = []
            for row in rows:
                v = json.loads(row["vector_json"])
                score = self.cosine_similarity(query_vector, v)
                scored_results.append({
                    "chunk_id": row["chunk_id"],
                    "memory_id": row["memory_id"],
                    "content": row["content"],
                    "score": round(score, 4)
                })

            scored_results.sort(key=lambda r: r["score"], reverse=True)
            return scored_results[:top_k]

    async def search_vectors(self, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        return await self._run_sync(self._search_vectors_sync, query_vector, top_k)

    def _delete_vector_sync(self, chunk_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM vector_embeddings WHERE chunk_id = ?", (chunk_id,))
            conn.commit()
            return cursor.rowcount > 0

    async def delete_vector(self, chunk_id: str) -> bool:
        return await self._run_sync(self._delete_vector_sync, chunk_id)
