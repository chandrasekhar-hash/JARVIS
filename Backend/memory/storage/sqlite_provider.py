import os
import sqlite3
import json
import time
import asyncio
from typing import List, Optional, Dict, Any
from memory.models.memory import (
    Memory,
    MemoryChunk,
    MemoryMetadata,
    MemoryRelationship,
    MemoryType,
    RetentionPolicy,
)
from memory.models.query import MemorySummary
from memory.storage.base import BaseMemoryStorageProvider
from tools.telemetry import log_structured, backend_log


class SQLiteMemoryStorageProvider(BaseMemoryStorageProvider):
    """
    Production-ready SQLite implementation of BaseMemoryStorageProvider for persistent memory,
    metadata, chunk, and relationship storage across process restarts.
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
            # 1. Memories table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    memory_id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    summary TEXT,
                    importance_score REAL,
                    confidence REAL,
                    created_at REAL,
                    updated_at REAL,
                    last_accessed REAL,
                    access_count INTEGER,
                    expires_at REAL,
                    pinned INTEGER,
                    source TEXT,
                    retention_policy TEXT,
                    privacy_level TEXT,
                    tags_json TEXT
                )
            """)
            # 2. Chunks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    memory_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    chunk_index INTEGER,
                    embedding_json TEXT,
                    FOREIGN KEY(memory_id) REFERENCES memories(memory_id) ON DELETE CASCADE
                )
            """)
            # 3. Relationships table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory_relationships (
                    relationship_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    weight REAL
                )
            """)
            conn.commit()

    async def _run_sync(self, func, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    # ── Relational Memory Operations ─────────────────────────────────────────

    def _store_memory_sync(self, memory: Memory) -> str:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            meta = memory.metadata
            cursor.execute("""
                INSERT OR REPLACE INTO memories (
                    memory_id, type, title, content, summary,
                    importance_score, confidence, created_at, updated_at,
                    last_accessed, access_count, expires_at, pinned,
                    source, retention_policy, privacy_level, tags_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory.memory_id,
                memory.type.value,
                memory.title,
                memory.content,
                memory.summary,
                meta.importance_score,
                meta.confidence,
                meta.created_at,
                meta.updated_at,
                meta.last_accessed,
                meta.access_count,
                meta.expires_at,
                1 if meta.pinned else 0,
                meta.source,
                meta.retention_policy.value,
                meta.privacy_level,
                json.dumps(meta.tags)
            ))

            # Store Chunks
            for chunk in memory.chunks:
                emb_json = json.dumps(chunk.embedding) if chunk.embedding is not None else None
                cursor.execute("""
                    INSERT OR REPLACE INTO memory_chunks (chunk_id, memory_id, content, chunk_index, embedding_json)
                    VALUES (?, ?, ?, ?, ?)
                """, (chunk.chunk_id, memory.memory_id, chunk.content, chunk.chunk_index, emb_json))

            conn.commit()
        return memory.memory_id

    async def store_memory(self, memory: Memory) -> str:
        return await self._run_sync(self._store_memory_sync, memory)

    def _get_memory_sync(self, memory_id: str) -> Optional[Memory]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM memories WHERE memory_id = ?", (memory_id,))
            row = cursor.fetchone()
            if not row:
                return None

            # Update access count & timestamp
            now = time.time()
            cursor.execute("UPDATE memories SET access_count = access_count + 1, last_accessed = ? WHERE memory_id = ?", (now, memory_id))
            conn.commit()

            # Load chunks
            cursor.execute("SELECT * FROM memory_chunks WHERE memory_id = ? ORDER BY chunk_index ASC", (memory_id,))
            chunk_rows = cursor.fetchall()
            chunks = []
            for crow in chunk_rows:
                emb = json.loads(crow["embedding_json"]) if crow["embedding_json"] else None
                chunks.append(MemoryChunk(
                    chunk_id=crow["chunk_id"],
                    memory_id=crow["memory_id"],
                    content=crow["content"],
                    embedding=emb,
                    chunk_index=crow["chunk_index"]
                ))

            tags = json.loads(row["tags_json"]) if row["tags_json"] else []
            meta = MemoryMetadata(
                importance_score=row["importance_score"],
                confidence=row["confidence"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                last_accessed=now,
                access_count=row["access_count"] + 1,
                expires_at=row["expires_at"],
                pinned=bool(row["pinned"]),
                source=row["source"],
                retention_policy=RetentionPolicy(row["retention_policy"]),
                privacy_level=row["privacy_level"],
                tags=tags
            )

            return Memory(
                memory_id=row["memory_id"],
                type=MemoryType(row["type"]),
                title=row["title"],
                content=row["content"],
                summary=row["summary"] or "",
                chunks=chunks,
                metadata=meta
            )

    async def get_memory(self, memory_id: str) -> Optional[Memory]:
        return await self._run_sync(self._get_memory_sync, memory_id)

    def _update_memory_sync(self, memory_id: str, updates: Dict[str, Any]) -> Optional[Memory]:
        memory = self._get_memory_sync(memory_id)
        if not memory:
            return None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            for key, val in updates.items():
                if key in ("title", "content", "summary"):
                    cursor.execute(f"UPDATE memories SET {key} = ? WHERE memory_id = ?", (val, memory_id))
                elif key in ("importance_score", "confidence", "source", "privacy_level"):
                    cursor.execute(f"UPDATE memories SET {key} = ? WHERE memory_id = ?", (val, memory_id))
                elif key == "tags":
                    cursor.execute("UPDATE memories SET tags_json = ? WHERE memory_id = ?", (json.dumps(val), memory_id))
                elif key == "pinned":
                    cursor.execute("UPDATE memories SET pinned = ? WHERE memory_id = ?", (1 if val else 0, memory_id))

            cursor.execute("UPDATE memories SET updated_at = ? WHERE memory_id = ?", (time.time(), memory_id))
            conn.commit()

        return self._get_memory_sync(memory_id)

    async def update_memory(self, memory_id: str, updates: Dict[str, Any]) -> Optional[Memory]:
        return await self._run_sync(self._update_memory_sync, memory_id, updates)

    def _delete_memory_sync(self, memory_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memory_chunks WHERE memory_id = ?", (memory_id,))
            cursor.execute("DELETE FROM memories WHERE memory_id = ?", (memory_id,))
            conn.commit()
            return cursor.rowcount > 0

    async def delete_memory(self, memory_id: str) -> bool:
        return await self._run_sync(self._delete_memory_sync, memory_id)

    def _archive_memory_sync(self, memory_id: str) -> bool:
        memory = self._get_memory_sync(memory_id)
        if not memory:
            return False
        
        tags = memory.metadata.tags
        if "archived" not in tags:
            tags.append("archived")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE memories SET tags_json = ?, updated_at = ? WHERE memory_id = ?", (json.dumps(tags), time.time(), memory_id))
            conn.commit()
            return True

    async def archive_memory(self, memory_id: str) -> bool:
        return await self._run_sync(self._archive_memory_sync, memory_id)

    def _list_memories_sync(
        self,
        memory_type: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Memory]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT memory_id FROM memories"
            params = []
            conditions = []

            if memory_type:
                conditions.append("type = ?")
                params.append(memory_type.lower())
            if tag:
                conditions.append("tags_json LIKE ?")
                params.append(f'%"{tag}"%')

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            memories = []
            for r in rows:
                mem = self._get_memory_sync(r["memory_id"])
                if mem:
                    memories.append(mem)
            return memories

    async def list_memories(
        self,
        memory_type: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Memory]:
        return await self._run_sync(self._list_memories_sync, memory_type, tag, limit, offset)

    def _get_summary_sync(self) -> MemorySummary:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total FROM memories")
            total = cursor.fetchone()["total"]

            cursor.execute("SELECT type, COUNT(*) as count FROM memories GROUP BY type")
            type_rows = cursor.fetchall()
            type_counts = {r["type"]: r["count"] for r in type_rows}

            cursor.execute("SELECT SUM(LENGTH(content)) as total_bytes FROM memories")
            bytes_row = cursor.fetchone()
            total_bytes = bytes_row["total_bytes"] if bytes_row and bytes_row["total_bytes"] else 0

            return MemorySummary(
                total_memories=total,
                count_by_type=type_counts,
                total_nodes=0,
                total_edges=0,
                storage_bytes=total_bytes
            )

    async def get_summary(self) -> MemorySummary:
        return await self._run_sync(self._get_summary_sync)
