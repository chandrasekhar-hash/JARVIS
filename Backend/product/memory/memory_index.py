"""
In-Memory Fast Indexing for Phase P1.2 (Memory & Personalization).
Maintains lightweight index buckets for rapid memory lookup by category, tags, and pinned state.
"""
import logging
from typing import Dict, List, Set, Optional
from .memory_models import Memory, MemoryCategory, MemoryType, MemoryStatus

logger = logging.getLogger("JARVIS_MemoryIndex")


class MemoryIndex:
    """
    In-memory search index data structure.
    Indexes memories by user ID, category, tags, and pinned state for fast search scoring.
    """

    def __init__(self):
        self._user_index: Dict[str, Dict[str, Memory]] = {}
        self._tag_index: Dict[str, Dict[str, Set[str]]] = {}

    def index_memory(self, memory: Memory) -> None:
        """Indexes or updates a memory entry in the in-memory cache."""
        user_id = memory.user_id
        if user_id not in self._user_index:
            self._user_index[user_id] = {}
            self._tag_index[user_id] = {}

        self._user_index[user_id][memory.memory_id] = memory

        # Tag indexing
        for tag in memory.tags or []:
            clean_tag = tag.strip().lower()
            if clean_tag not in self._tag_index[user_id]:
                self._tag_index[user_id][clean_tag] = set()
            self._tag_index[user_id][clean_tag].add(memory.memory_id)

    def remove_from_index(self, user_id: str, memory_id: str) -> None:
        """Removes a memory entry from the index."""
        if user_id in self._user_index and memory_id in self._user_index[user_id]:
            mem = self._user_index[user_id].pop(memory_id)
            for tag in mem.tags or []:
                clean_tag = tag.strip().lower()
                if clean_tag in self._tag_index[user_id]:
                    self._tag_index[user_id][clean_tag].discard(memory_id)

    def clear_user(self, user_id: str) -> None:
        """Clears all indexed memories for a user ID."""
        if user_id in self._user_index:
            del self._user_index[user_id]
        if user_id in self._tag_index:
            del self._tag_index[user_id]
