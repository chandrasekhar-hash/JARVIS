"""
SQLite Memory Repository Engine for Phase P1.2 (Memory & Personalization).
Implements thread-safe SQLite persistence for memories, tags, links, collections, settings, and personalization profiles.
Enforces 100% user data isolation across all database operations.
"""
import json
import sqlite3
import time
import logging
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager

from .memory_models import (
    Memory,
    MemoryCategory,
    MemoryType,
    MemoryStatus,
    RetentionPolicy,
    MemoryCollection,
    MemorySettings,
    PersonalizationProfile,
)
from .memory_interfaces import (
    IMemoryRepository,
    IPersonalizationRepository,
    IMemorySettingsRepository,
)
from .memory_migration import MemorySchemaMigration

logger = logging.getLogger("JARVIS_SQLiteMemoryRepository")


class SQLiteMemoryRepository(
    IMemoryRepository,
    IPersonalizationRepository,
    IMemorySettingsRepository,
):
    """
    SQLite persistence implementation for all Phase P1.2 Memory & Personalization models.
    Guarantees user-level security isolation and automated expiration eviction.
    """

    def __init__(self, product_storage_instance):
        self.storage = product_storage_instance
        # Ensure database schema is migrated to version 2
        MemorySchemaMigration.migrate(self.storage)

    @contextmanager
    def _get_connection(self):
        """Reuses the connection manager from ProductStorage."""
        with self.storage._get_connection() as conn:
            yield conn

    # -------------------------------------------------------------------------
    # IMemoryRepository Implementation
    # -------------------------------------------------------------------------
    def create_memory(self, memory: Memory) -> Memory:
        tags_json = json.dumps(memory.tags or [])
        metadata_json = json.dumps(memory.metadata or {})

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO memories (
                    memory_id, user_id, category, type, title, content, tags,
                    importance_score, confidence_score, is_pinned, retention_policy,
                    expires_at, created_at, updated_at, last_accessed, access_count,
                    reinforcement_count, source, status, version, superseded_by,
                    collection_id, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory.memory_id,
                    memory.user_id,
                    memory.category.value if isinstance(memory.category, MemoryCategory) else str(memory.category),
                    memory.type.value if isinstance(memory.type, MemoryType) else str(memory.type),
                    memory.title,
                    memory.content,
                    tags_json,
                    memory.importance_score,
                    memory.confidence_score,
                    1 if memory.is_pinned else 0,
                    memory.retention_policy.value if isinstance(memory.retention_policy, RetentionPolicy) else str(memory.retention_policy),
                    memory.expires_at,
                    memory.created_at,
                    memory.updated_at,
                    memory.last_accessed,
                    memory.access_count,
                    memory.reinforcement_count,
                    memory.source,
                    memory.status.value if isinstance(memory.status, MemoryStatus) else str(memory.status),
                    memory.version,
                    memory.superseded_by,
                    memory.collection_id,
                    metadata_json,
                ),
            )

            # Insert tag mappings
            for tag in memory.tags or []:
                tag_id = f"tag_{memory.memory_id}_{tag.strip()}"
                conn.execute(
                    "INSERT OR IGNORE INTO memory_tags (tag_id, memory_id, tag_name, created_at) VALUES (?, ?, ?, ?)",
                    (tag_id, memory.memory_id, tag.strip(), time.time()),
                )

        return memory

    def get_memory_by_id(self, user_id: str, memory_id: str) -> Optional[Memory]:
        self.evict_expired_memories(user_id)
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM memories WHERE memory_id = ? AND user_id = ?",
                (memory_id, user_id),
            ).fetchone()
            if row:
                # Update last_accessed and access_count
                now = time.time()
                conn.execute(
                    "UPDATE memories SET last_accessed = ?, access_count = access_count + 1 WHERE memory_id = ?",
                    (now, memory_id),
                )
                mem = self._row_to_memory(row)
                mem.last_accessed = now
                mem.access_count += 1
                return mem
        return None

    def update_memory(self, memory: Memory) -> Memory:
        memory.updated_at = time.time()
        tags_json = json.dumps(memory.tags or [])
        metadata_json = json.dumps(memory.metadata or {})

        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE memories
                SET category = ?, type = ?, title = ?, content = ?, tags = ?,
                    importance_score = ?, confidence_score = ?, is_pinned = ?,
                    retention_policy = ?, expires_at = ?, updated_at = ?,
                    last_accessed = ?, access_count = ?, reinforcement_count = ?,
                    source = ?, status = ?, version = ?, superseded_by = ?,
                    collection_id = ?, metadata = ?
                WHERE memory_id = ? AND user_id = ?
                """,
                (
                    memory.category.value if isinstance(memory.category, MemoryCategory) else str(memory.category),
                    memory.type.value if isinstance(memory.type, MemoryType) else str(memory.type),
                    memory.title,
                    memory.content,
                    tags_json,
                    memory.importance_score,
                    memory.confidence_score,
                    1 if memory.is_pinned else 0,
                    memory.retention_policy.value if isinstance(memory.retention_policy, RetentionPolicy) else str(memory.retention_policy),
                    memory.expires_at,
                    memory.updated_at,
                    memory.last_accessed,
                    memory.access_count,
                    memory.reinforcement_count,
                    memory.source,
                    memory.status.value if isinstance(memory.status, MemoryStatus) else str(memory.status),
                    memory.version,
                    memory.superseded_by,
                    memory.collection_id,
                    metadata_json,
                    memory.memory_id,
                    memory.user_id,
                ),
            )
        return memory

    def delete_memory(self, user_id: str, memory_id: str) -> bool:
        with self._get_connection() as conn:
            res = conn.execute(
                "DELETE FROM memories WHERE memory_id = ? AND user_id = ?",
                (memory_id, user_id),
            )
            return res.rowcount > 0

    def archive_memory(self, user_id: str, memory_id: str) -> bool:
        with self._get_connection() as conn:
            res = conn.execute(
                "UPDATE memories SET status = 'ARCHIVED', updated_at = ? WHERE memory_id = ? AND user_id = ?",
                (time.time(), memory_id, user_id),
            )
            return res.rowcount > 0

    def restore_memory(self, user_id: str, memory_id: str) -> bool:
        with self._get_connection() as conn:
            res = conn.execute(
                "UPDATE memories SET status = 'ACTIVE', updated_at = ? WHERE memory_id = ? AND user_id = ?",
                (time.time(), memory_id, user_id),
            )
            return res.rowcount > 0

    def supersede_memory(
        self, user_id: str, old_memory_id: str, new_memory: Memory
    ) -> Tuple[Optional[Memory], Memory]:
        """
        Marks old memory as SUPERSEDED by new_memory.id, increments versioning,
        and creates the new Memory record.
        """
        old_mem = self.get_memory_by_id(user_id, old_memory_id)
        if old_mem:
            old_mem.status = MemoryStatus.SUPERSEDED
            old_mem.superseded_by = new_memory.memory_id
            self.update_memory(old_mem)

        new_memory.version = (old_mem.version + 1) if old_mem else 1
        created_new = self.create_memory(new_memory)
        return old_mem, created_new

    def reinforce_confidence(self, user_id: str, memory_id: str, boost: float = 0.05) -> Optional[Memory]:
        """Increments confidence_score (capped at 1.0) and reinforcement_count."""
        mem = self.get_memory_by_id(user_id, memory_id)
        if not mem:
            return None

        mem.confidence_score = min(1.0, mem.confidence_score + boost)
        mem.reinforcement_count += 1
        mem.last_accessed = time.time()
        return self.update_memory(mem)

    def list_memories(
        self,
        user_id: str,
        category: Optional[MemoryCategory] = None,
        memory_type: Optional[MemoryType] = None,
        status: Optional[MemoryStatus] = MemoryStatus.ACTIVE,
        collection_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Memory]:
        self.evict_expired_memories(user_id)
        sql = "SELECT * FROM memories WHERE user_id = ?"
        params: List[Any] = [user_id]

        if category:
            sql += " AND category = ?"
            params.append(category.value if isinstance(category, MemoryCategory) else str(category))
        if memory_type:
            sql += " AND type = ?"
            params.append(memory_type.value if isinstance(memory_type, MemoryType) else str(memory_type))
        if status:
            sql += " AND status = ?"
            params.append(status.value if isinstance(status, MemoryStatus) else str(status))
        if collection_id:
            sql += " AND collection_id = ?"
            params.append(collection_id)

        sql += " ORDER BY is_pinned DESC, importance_score DESC, updated_at DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_memory(r) for r in rows]

    def pin_memory(self, user_id: str, memory_id: str) -> bool:
        with self._get_connection() as conn:
            res = conn.execute(
                "UPDATE memories SET is_pinned = 1, updated_at = ? WHERE memory_id = ? AND user_id = ?",
                (time.time(), memory_id, user_id),
            )
            return res.rowcount > 0

    def unpin_memory(self, user_id: str, memory_id: str) -> bool:
        with self._get_connection() as conn:
            res = conn.execute(
                "UPDATE memories SET is_pinned = 0, updated_at = ? WHERE memory_id = ? AND user_id = ?",
                (time.time(), memory_id, user_id),
            )
            return res.rowcount > 0

    def clear_user_memories(self, user_id: str) -> int:
        with self._get_connection() as conn:
            res = conn.execute("DELETE FROM memories WHERE user_id = ?", (user_id,))
            return res.rowcount

    def evict_expired_memories(self, user_id: str) -> int:
        now = time.time()
        with self._get_connection() as conn:
            res = conn.execute(
                "DELETE FROM memories WHERE user_id = ? AND expires_at IS NOT NULL AND expires_at <= ?",
                (user_id, now),
            )
            return res.rowcount

    def _row_to_memory(self, row: sqlite3.Row) -> Memory:
        tags = json.loads(row["tags"]) if row["tags"] else []
        meta = json.loads(row["metadata"]) if row["metadata"] else {}
        return Memory(
            memory_id=row["memory_id"],
            user_id=row["user_id"],
            category=MemoryCategory(row["category"]),
            type=MemoryType(row["type"]),
            title=row["title"],
            content=row["content"],
            tags=tags,
            importance_score=row["importance_score"],
            confidence_score=row["confidence_score"],
            is_pinned=bool(row["is_pinned"]),
            retention_policy=RetentionPolicy(row["retention_policy"]),
            expires_at=row["expires_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_accessed=row["last_accessed"],
            access_count=row["access_count"],
            reinforcement_count=row["reinforcement_count"] if "reinforcement_count" in row.keys() else 1,
            source=row["source"],
            status=MemoryStatus(row["status"]),
            version=row["version"],
            superseded_by=row["superseded_by"],
            collection_id=row["collection_id"],
            metadata=meta,
        )

    # -------------------------------------------------------------------------
    # IPersonalizationRepository Implementation
    # -------------------------------------------------------------------------
    def get_profile(self, user_id: str) -> Optional[PersonalizationProfile]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM personalization_profiles WHERE user_id = ?", (user_id,)
            ).fetchone()
            if row:
                topics = json.loads(row["favorite_topics"]) if row["favorite_topics"] else []
                prod = json.loads(row["productivity_preferences"]) if row["productivity_preferences"] else {}
                learn = json.loads(row["learning_preferences"]) if row["learning_preferences"] else {}
                code = json.loads(row["coding_preferences"]) if row["coding_preferences"] else {}
                notif = json.loads(row["notification_behavior"]) if row["notification_behavior"] else {}

                return PersonalizationProfile(
                    user_id=row["user_id"],
                    preferred_assistant_name=row["preferred_assistant_name"],
                    preferred_wake_word=row["preferred_wake_word"],
                    communication_style=row["communication_style"],
                    preferred_language=row["preferred_language"],
                    preferred_ai_model=row["preferred_ai_model"],
                    favorite_topics=topics,
                    productivity_preferences=prod,
                    learning_preferences=learn,
                    coding_preferences=code,
                    notification_behavior=notif,
                    conversation_tone=row["conversation_tone"],
                    updated_at=row["updated_at"],
                )
        return None

    def save_profile(self, profile: PersonalizationProfile) -> PersonalizationProfile:
        profile.updated_at = time.time()
        topics_json = json.dumps(profile.favorite_topics or [])
        prod_json = json.dumps(profile.productivity_preferences or {})
        learn_json = json.dumps(profile.learning_preferences or {})
        code_json = json.dumps(profile.coding_preferences or {})
        notif_json = json.dumps(profile.notification_behavior or {})

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO personalization_profiles (
                    user_id, preferred_assistant_name, preferred_wake_word, communication_style,
                    preferred_language, preferred_ai_model, favorite_topics, productivity_preferences,
                    learning_preferences, coding_preferences, notification_behavior,
                    conversation_tone, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    preferred_assistant_name = excluded.preferred_assistant_name,
                    preferred_wake_word = excluded.preferred_wake_word,
                    communication_style = excluded.communication_style,
                    preferred_language = excluded.preferred_language,
                    preferred_ai_model = excluded.preferred_ai_model,
                    favorite_topics = excluded.favorite_topics,
                    productivity_preferences = excluded.productivity_preferences,
                    learning_preferences = excluded.learning_preferences,
                    coding_preferences = excluded.coding_preferences,
                    notification_behavior = excluded.notification_behavior,
                    conversation_tone = excluded.conversation_tone,
                    updated_at = excluded.updated_at
                """,
                (
                    profile.user_id,
                    profile.preferred_assistant_name,
                    profile.preferred_wake_word,
                    profile.communication_style,
                    profile.preferred_language,
                    profile.preferred_ai_model,
                    topics_json,
                    prod_json,
                    learn_json,
                    code_json,
                    notif_json,
                    profile.conversation_tone,
                    profile.updated_at,
                ),
            )
        return profile

    # -------------------------------------------------------------------------
    # IMemorySettingsRepository Implementation
    # -------------------------------------------------------------------------
    def get_settings(self, user_id: str) -> MemorySettings:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM memory_settings WHERE user_id = ?", (user_id,)
            ).fetchone()
            if row:
                return MemorySettings(
                    user_id=row["user_id"],
                    memory_enabled=bool(row["memory_enabled"]),
                    auto_summarize=bool(row["auto_summarize"]),
                    max_working_memory_items=row["max_working_memory_items"],
                    retention_days=row["retention_days"],
                    privacy_opt_out=bool(row["privacy_opt_out"]),
                    updated_at=row["updated_at"],
                )
        return MemorySettings(user_id=user_id)

    def save_settings(self, settings: MemorySettings) -> MemorySettings:
        settings.updated_at = time.time()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO memory_settings (
                    user_id, memory_enabled, auto_summarize, max_working_memory_items,
                    retention_days, privacy_opt_out, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    memory_enabled = excluded.memory_enabled,
                    auto_summarize = excluded.auto_summarize,
                    max_working_memory_items = excluded.max_working_memory_items,
                    retention_days = excluded.retention_days,
                    privacy_opt_out = excluded.privacy_opt_out,
                    updated_at = excluded.updated_at
                """,
                (
                    settings.user_id,
                    1 if settings.memory_enabled else 0,
                    1 if settings.auto_summarize else 0,
                    settings.max_working_memory_items,
                    settings.retention_days,
                    1 if settings.privacy_opt_out else 0,
                    settings.updated_at,
                ),
            )
        return settings
