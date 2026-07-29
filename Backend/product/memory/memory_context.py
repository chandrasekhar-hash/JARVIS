"""
Working Memory & Context Window Builder for Phase P1.2 (Memory & Personalization).
Constructs contextual memory payloads for V1.3 Conversation Engine and V1.6 Voice Orchestrator.
"""
import logging
from typing import Dict, Any, List, Optional

from .memory_models import Memory, MemoryCategory, MemoryType, MemoryStatus
from .memory_interfaces import IMemoryContextBuilder, IMemoryRepository, IPersonalizationRepository

logger = logging.getLogger("JARVIS_MemoryContextBuilder")


class MemoryContextBuilder(IMemoryContextBuilder):
    """
    Constructs user-scoped memory context payloads.
    Retrieves active pinned memories, personal facts, preferences, and relevant working memory context.
    """

    def __init__(
        self,
        memory_repository: IMemoryRepository,
        personalization_repository: Optional[IPersonalizationRepository] = None,
    ):
        self.memory_repo = memory_repository
        self.personalization_repo = personalization_repository

    def build_context_window(
        self, user_id: str, current_query: str, max_items: int = 10
    ) -> Dict[str, Any]:
        """
        Constructs context payload for conversation processing.
        """
        # Fetch active memories for user
        active_memories = self.memory_repo.list_memories(
            user_id=user_id,
            status=MemoryStatus.ACTIVE,
            limit=50,
        )

        pinned = [m.to_dict() for m in active_memories if m.is_pinned]
        user_facts = [
            m.to_dict() for m in active_memories
            if m.category == MemoryCategory.USER_MEMORY and m.type == MemoryType.LONG_TERM and not m.is_pinned
        ][:max_items]
        working_mem = [
            m.to_dict() for m in active_memories
            if m.type == MemoryType.WORKING
        ][:max_items]

        personalization = None
        if self.personalization_repo:
            profile = self.personalization_repo.get_profile(user_id)
            if profile:
                personalization = profile.to_dict()

        return {
            "user_id": user_id,
            "query": current_query,
            "pinned_memories": pinned,
            "user_facts": user_facts,
            "working_memory": working_mem,
            "personalization": personalization,
        }
