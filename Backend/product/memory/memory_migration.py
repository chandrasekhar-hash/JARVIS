"""
Database Schema Migration Manager for Phase P1.2 (Memory & Personalization).
Upgrades SQLite database schema from version 1 to version 2 using schema_metadata version tracking.
"""
import time
import logging
import sqlite3
from typing import Optional

logger = logging.getLogger("JARVIS_MemoryMigration")


class MemorySchemaMigration:
    """
    Handles seamless migration of the J.A.R.V.I.S. Product database schema to Version 2.
    """

    TARGET_VERSION = 2

    @classmethod
    def migrate(cls, storage_instance) -> bool:
        """
        Executes schema migration to version 2 if current schema_version is less than 2.
        """
        current_version = storage_instance.get_schema_version()
        if current_version >= cls.TARGET_VERSION:
            logger.info(f"[MemorySchemaMigration] Schema already up-to-date (Version {current_version}).")
            return True

        logger.info(f"[MemorySchemaMigration] Upgrading database schema from Version {current_version} to {cls.TARGET_VERSION}...")
        now = time.time()

        with storage_instance._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS memories (
                    memory_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'USER_MEMORY',
                    type TEXT NOT NULL DEFAULT 'LONG_TERM',
                    title TEXT DEFAULT '',
                    content TEXT DEFAULT '',
                    tags TEXT DEFAULT '[]',
                    importance_score REAL DEFAULT 0.5,
                    confidence_score REAL DEFAULT 0.6,
                    is_pinned INTEGER DEFAULT 0,
                    retention_policy TEXT DEFAULT 'PERMANENT',
                    expires_at REAL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    last_accessed REAL NOT NULL,
                    access_count INTEGER DEFAULT 1,
                    reinforcement_count INTEGER DEFAULT 1,
                    source TEXT DEFAULT 'user_input',
                    status TEXT DEFAULT 'ACTIVE',
                    version INTEGER DEFAULT 1,
                    superseded_by TEXT,
                    collection_id TEXT,
                    metadata TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS memory_tags (
                    tag_id TEXT PRIMARY KEY,
                    memory_id TEXT NOT NULL,
                    tag_name TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY(memory_id) REFERENCES memories(memory_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS memory_links (
                    link_id TEXT PRIMARY KEY,
                    source_memory_id TEXT NOT NULL,
                    target_memory_id TEXT NOT NULL,
                    relation_type TEXT DEFAULT 'related',
                    created_at REAL NOT NULL,
                    FOREIGN KEY(source_memory_id) REFERENCES memories(memory_id) ON DELETE CASCADE,
                    FOREIGN KEY(target_memory_id) REFERENCES memories(memory_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS memory_collections (
                    collection_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    color TEXT DEFAULT '#4A90E2',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS memory_settings (
                    user_id TEXT PRIMARY KEY,
                    memory_enabled INTEGER DEFAULT 1,
                    auto_summarize INTEGER DEFAULT 1,
                    max_working_memory_items INTEGER DEFAULT 10,
                    retention_days INTEGER DEFAULT 365,
                    privacy_opt_out INTEGER DEFAULT 0,
                    updated_at REAL NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS personalization_profiles (
                    user_id TEXT PRIMARY KEY,
                    preferred_assistant_name TEXT DEFAULT 'J.A.R.V.I.S.',
                    preferred_wake_word TEXT DEFAULT 'JARVIS',
                    communication_style TEXT DEFAULT 'concise_professional',
                    preferred_language TEXT DEFAULT 'en-US',
                    preferred_ai_model TEXT DEFAULT 'gemini-2.5-flash',
                    favorite_topics TEXT DEFAULT '[]',
                    productivity_preferences TEXT DEFAULT '{}',
                    learning_preferences TEXT DEFAULT '{}',
                    coding_preferences TEXT DEFAULT '{}',
                    notification_behavior TEXT DEFAULT '{}',
                    conversation_tone TEXT DEFAULT 'helpful',
                    updated_at REAL NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id);
                CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
                CREATE INDEX IF NOT EXISTS idx_memories_status ON memories(status);
                CREATE INDEX IF NOT EXISTS idx_memories_pinned ON memories(is_pinned);
                CREATE INDEX IF NOT EXISTS idx_memory_tags_name ON memory_tags(tag_name);
            """)

            # Update schema_metadata
            conn.execute(
                "UPDATE schema_metadata SET schema_version = ?, updated_at = ?",
                (cls.TARGET_VERSION, now),
            )

        logger.info(f"[MemorySchemaMigration] Successfully upgraded database schema to Version {cls.TARGET_VERSION}.")
        return True
