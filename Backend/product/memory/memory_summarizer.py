"""
Memory Summarizer, Merging, and Splitting Service for Phase P1.2 (Memory & Personalization).
Handles consolidating session memories, merging multiple memories while preserving conflict versioning,
and splitting complex memory blocks into distinct records.
"""
import time
import uuid
import logging
from typing import List, Optional

from .memory_models import (
    Memory,
    MemoryCategory,
    MemoryType,
    MemoryStatus,
    RetentionPolicy,
)
from .memory_interfaces import IMemorySummarizer, IMemoryRepository

logger = logging.getLogger("JARVIS_MemorySummarizer")


class MemorySummarizer(IMemorySummarizer):
    """
    Memory Summarizer domain service.
    Coordinates memory summarization, multi-record merging with superseded tracking, and splitting.
    """

    def __init__(self, repository: IMemoryRepository):
        self.repository = repository

    def summarize_memories(self, memories: List[Memory]) -> str:
        """
        Generates a concise summary string across a list of memories.
        """
        if not memories:
            return "No memory records provided."

        summary_lines = []
        for mem in memories:
            title_str = f"[{mem.title}] " if mem.title else ""
            summary_lines.append(f"- {title_str}{mem.content[:150]}")

        return "\n".join(summary_lines)

    def merge_memories(self, user_id: str, memories: List[Memory], merged_title: str) -> Memory:
        """
        Merges multiple memories into a single consolidated Memory.
        Marks old memories as SUPERSEDED and links them to the new memory ID.
        """
        if not memories:
            raise ValueError("At least one memory must be provided for merging.")

        merged_content_blocks = [mem.content for mem in memories if mem.content]
        combined_content = "\n\n".join(merged_content_blocks)

        # Collect unique tags
        all_tags = set()
        for mem in memories:
            if mem.tags:
                all_tags.update(mem.tags)

        # Compute max importance & confidence
        max_importance = max(mem.importance_score for mem in memories)
        max_confidence = max(mem.confidence_score for mem in memories)

        new_mem_id = f"mem_{str(uuid.uuid4())}"
        now = time.time()

        merged_memory = Memory(
            memory_id=new_mem_id,
            user_id=user_id,
            category=memories[0].category,
            type=MemoryType.LONG_TERM,
            title=merged_title,
            content=combined_content,
            tags=list(all_tags),
            importance_score=max_importance,
            confidence_score=max_confidence,
            is_pinned=any(m.is_pinned for m in memories),
            retention_policy=RetentionPolicy.PERMANENT,
            created_at=now,
            updated_at=now,
            last_accessed=now,
            source="memory_merge",
            status=MemoryStatus.ACTIVE,
            version=1,
        )

        created_merged = self.repository.create_memory(merged_memory)

        # Mark source memories as SUPERSEDED
        for old_mem in memories:
            old_mem.status = MemoryStatus.SUPERSEDED
            old_mem.superseded_by = created_merged.memory_id
            self.repository.update_memory(old_mem)

        logger.info(
            f"[MemorySummarizer] Successfully merged {len(memories)} memories into new memory '{created_merged.memory_id}'."
        )
        return created_merged

    def split_memory(self, user_id: str, memory_id: str, split_delimiter: str = "\n\n") -> List[Memory]:
        """
        Splits a single memory into multiple smaller sub-memories.
        """
        original = self.repository.get_memory_by_id(user_id, memory_id)
        if not original:
            raise ValueError(f"Memory '{memory_id}' not found for user '{user_id}'.")

        chunks = [c.strip() for c in original.content.split(split_delimiter) if c.strip()]
        if len(chunks) <= 1:
            return [original]

        split_memories: List[Memory] = []
        now = time.time()

        for idx, chunk in enumerate(chunks, 1):
            sub_id = f"mem_{str(uuid.uuid4())}"
            sub_mem = Memory(
                memory_id=sub_id,
                user_id=user_id,
                category=original.category,
                type=original.type,
                title=f"{original.title} (Part {idx})" if original.title else f"Part {idx}",
                content=chunk,
                tags=original.tags.copy() if original.tags else [],
                importance_score=original.importance_score,
                confidence_score=original.confidence_score,
                is_pinned=False,
                retention_policy=original.retention_policy,
                created_at=now,
                updated_at=now,
                last_accessed=now,
                source="memory_split",
                status=MemoryStatus.ACTIVE,
                version=1,
            )
            created_sub = self.repository.create_memory(sub_mem)
            split_memories.append(created_sub)

        # Mark original as SUPERSEDED
        original.status = MemoryStatus.SUPERSEDED
        original.superseded_by = split_memories[0].memory_id
        self.repository.update_memory(original)

        logger.info(
            f"[MemorySummarizer] Successfully split memory '{memory_id}' into {len(split_memories)} sub-memories."
        )
        return split_memories
