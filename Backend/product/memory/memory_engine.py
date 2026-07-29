"""
Public API Entrypoint for Phase P1.2 (Memory & Personalization).
Coordinates Memory CRUD, Hybrid Search, Personalization Profiles, Summarization,
Privacy Controls, and EventBus event broadcasting.
"""
import uuid
import time
import logging
from typing import Optional, Dict, Any, List, Tuple

from .memory_models import (
    Memory,
    MemoryCategory,
    MemoryType,
    MemoryStatus,
    RetentionPolicy,
    MemorySettings,
    PersonalizationProfile,
    MemorySearchResult,
)
from .memory_store import SQLiteMemoryRepository
from .memory_search import MemorySearchEngine
from .memory_summarizer import MemorySummarizer
from .memory_context import MemoryContextBuilder
from .memory_settings import MemorySettingsManager
from product.storage import SQLiteProductStorage
from brain.event_bus import event_bus, EventBus

logger = logging.getLogger("JARVIS_MemoryEngine")


class MemoryEngine:
    """
    Production-grade Memory & Personalization Public API Entrypoint for Phase P1.2.
    Integrates Memory Storage, Hybrid Search, Context Window Building, Privacy Controls, and EventBus.
    """

    def __init__(
        self,
        repository: Optional[SQLiteMemoryRepository] = None,
        bus: Optional[EventBus] = None,
        product_storage: Optional[SQLiteProductStorage] = None,
    ):
        self.event_bus = bus or event_bus
        if repository:
            self.repository = repository
        else:
            p_storage = product_storage or SQLiteProductStorage()
            self.repository = SQLiteMemoryRepository(product_storage_instance=p_storage)

        self.search_engine = MemorySearchEngine(repository=self.repository)
        self.summarizer = MemorySummarizer(repository=self.repository)
        self.context_builder = MemoryContextBuilder(
            memory_repository=self.repository,
            personalization_repository=self.repository,
        )
        self.settings_manager = MemorySettingsManager(
            settings_repository=self.repository,
            memory_repository=self.repository,
            personalization_repository=self.repository,
        )
        self._running: bool = False

    async def start(self) -> None:
        """Starts the Memory & Personalization engine service."""
        self._running = True
        logger.info("[MemoryEngine] Memory & Personalization service started successfully.")

    async def stop(self) -> None:
        """Stops the Memory & Personalization engine service cleanly."""
        self._running = False
        logger.info("[MemoryEngine] Memory & Personalization service stopped cleanly.")

    def create_memory(
        self,
        user_id: str,
        content: str,
        title: str = "",
        category: MemoryCategory = MemoryCategory.USER_MEMORY,
        memory_type: MemoryType = MemoryType.LONG_TERM,
        tags: Optional[List[str]] = None,
        importance_score: float = 0.5,
        confidence_score: float = 0.6,
        is_pinned: bool = False,
        retention_policy: RetentionPolicy = RetentionPolicy.PERMANENT,
        expires_at: Optional[float] = None,
        source: str = "user_input",
        collection_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Memory:
        """Creates and persists a new memory record and emits 'MemoryCreated' event."""
        # Check if memory feature is enabled
        settings = self.settings_manager.get_settings(user_id)
        if not settings.memory_enabled:
            logger.warning(f"[MemoryEngine] Memory creation skipped: feature disabled for user '{user_id}'.")

        mem_id = f"mem_{str(uuid.uuid4())}"
        now = time.time()

        memory = Memory(
            memory_id=mem_id,
            user_id=user_id,
            category=category,
            type=memory_type,
            title=title,
            content=content,
            tags=tags or [],
            importance_score=importance_score,
            confidence_score=confidence_score,
            is_pinned=is_pinned,
            retention_policy=retention_policy,
            expires_at=expires_at,
            created_at=now,
            updated_at=now,
            last_accessed=now,
            source=source,
            status=MemoryStatus.ACTIVE,
            collection_id=collection_id,
            metadata=metadata or {},
        )

        created = self.repository.create_memory(memory)
        self.event_bus.emit(
            "MemoryCreated",
            memory_id=created.memory_id,
            user_id=user_id,
            category=created.category.value,
            type=created.type.value,
        )
        return created

    def get_memory(self, user_id: str, memory_id: str) -> Optional[Memory]:
        """Retrieves a memory record by memory ID."""
        return self.repository.get_memory_by_id(user_id, memory_id)

    def update_memory(
        self,
        user_id: str,
        memory_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        importance_score: Optional[float] = None,
        confidence_score: Optional[float] = None,
        is_pinned: Optional[bool] = None,
    ) -> Memory:
        """Updates a memory record and emits 'MemoryUpdated' event."""
        mem = self.repository.get_memory_by_id(user_id, memory_id)
        if not mem:
            raise ValueError(f"Memory '{memory_id}' not found for user '{user_id}'.")

        if title is not None:
            mem.title = title
        if content is not None:
            mem.content = content
        if tags is not None:
            mem.tags = tags
        if importance_score is not None:
            mem.importance_score = importance_score
        if confidence_score is not None:
            mem.confidence_score = confidence_score
        if is_pinned is not None:
            mem.is_pinned = is_pinned

        updated = self.repository.update_memory(mem)
        self.event_bus.emit("MemoryUpdated", memory_id=memory_id, user_id=user_id)
        return updated

    def delete_memory(self, user_id: str, memory_id: str) -> bool:
        """Deletes a memory record and emits 'MemoryDeleted' event."""
        success = self.repository.delete_memory(user_id, memory_id)
        if success:
            self.event_bus.emit("MemoryDeleted", memory_id=memory_id, user_id=user_id)
        return success

    def archive_memory(self, user_id: str, memory_id: str) -> bool:
        """Archives a memory record and emits 'MemoryArchived' event."""
        success = self.repository.archive_memory(user_id, memory_id)
        if success:
            self.event_bus.emit("MemoryArchived", memory_id=memory_id, user_id=user_id)
        return success

    def restore_memory(self, user_id: str, memory_id: str) -> bool:
        """Restores an archived memory record and emits 'MemoryRestored' event."""
        success = self.repository.restore_memory(user_id, memory_id)
        if success:
            self.event_bus.emit("MemoryRestored", memory_id=memory_id, user_id=user_id)
        return success

    def search_memory(
        self,
        user_id: str,
        query: str,
        category: Optional[MemoryCategory] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20,
    ) -> MemorySearchResult:
        """Performs hybrid non-vector search across user memories."""
        return self.search_engine.search_memories(
            user_id=user_id,
            query=query,
            category=category,
            tags=tags,
            limit=limit,
        )

    def list_memories(
        self,
        user_id: str,
        category: Optional[MemoryCategory] = None,
        memory_type: Optional[MemoryType] = None,
        status: Optional[MemoryStatus] = MemoryStatus.ACTIVE,
        collection_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Memory]:
        """Lists user memories matching criteria."""
        return self.repository.list_memories(
            user_id=user_id,
            category=category,
            memory_type=memory_type,
            status=status,
            collection_id=collection_id,
            limit=limit,
        )

    def pin_memory(self, user_id: str, memory_id: str) -> bool:
        """Pins a memory record and emits 'MemoryPinned' event."""
        success = self.repository.pin_memory(user_id, memory_id)
        if success:
            self.event_bus.emit("MemoryPinned", memory_id=memory_id, user_id=user_id)
        return success

    def unpin_memory(self, user_id: str, memory_id: str) -> bool:
        """Unpins a memory record and emits 'MemoryUnpinned' event."""
        success = self.repository.unpin_memory(user_id, memory_id)
        if success:
            self.event_bus.emit("MemoryUnpinned", memory_id=memory_id, user_id=user_id)
        return success

    def summarize_memory(self, memories: List[Memory]) -> str:
        """Summarizes a set of memory records."""
        return self.summarizer.summarize_memories(memories)

    def merge_memories(self, user_id: str, memory_ids: List[str], merged_title: str) -> Memory:
        """Merges multiple memories and emits 'MemorySuperseded' event."""
        memories = []
        for mid in memory_ids:
            m = self.repository.get_memory_by_id(user_id, mid)
            if m:
                memories.append(m)

        merged = self.summarizer.merge_memories(user_id, memories, merged_title)
        self.event_bus.emit("MemorySuperseded", merged_memory_id=merged.memory_id, user_id=user_id)
        return merged

    def split_memory(self, user_id: str, memory_id: str, split_delimiter: str = "\n\n") -> List[Memory]:
        """Splits a single memory into sub-memories."""
        return self.summarizer.split_memory(user_id, memory_id, split_delimiter=split_delimiter)

    def reinforce_confidence(self, user_id: str, memory_id: str, boost: float = 0.05) -> Optional[Memory]:
        """Increments memory confidence score."""
        return self.repository.reinforce_confidence(user_id, memory_id, boost=boost)

    def export_memories(self, user_id: str) -> Dict[str, Any]:
        """Exports user memories and personalization profiles to JSON dictionary format."""
        return self.settings_manager.export_memories(user_id)

    def import_memories(self, user_id: str, import_data: Dict[str, Any]) -> Tuple[int, str]:
        """Imports memories from exported JSON dictionary structure."""
        return self.settings_manager.import_memories(user_id, import_data)

    def clear_memory(self, user_id: str) -> int:
        """Clears all memories for a user ID."""
        cleared = self.settings_manager.clear_all_memories(user_id)
        self.event_bus.emit("MemoryCleared", user_id=user_id, count=cleared)
        return cleared

    def get_personalization(self, user_id: str) -> PersonalizationProfile:
        """Retrieves or creates default PersonalizationProfile for user."""
        profile = self.repository.get_profile(user_id)
        if not profile:
            profile = PersonalizationProfile(user_id=user_id)
            self.repository.save_profile(profile)
        return profile

    def update_personalization(
        self,
        user_id: str,
        preferred_assistant_name: Optional[str] = None,
        preferred_wake_word: Optional[str] = None,
        communication_style: Optional[str] = None,
        preferred_language: Optional[str] = None,
        preferred_ai_model: Optional[str] = None,
        favorite_topics: Optional[List[str]] = None,
        productivity_preferences: Optional[Dict[str, Any]] = None,
        learning_preferences: Optional[Dict[str, Any]] = None,
        coding_preferences: Optional[Dict[str, Any]] = None,
        notification_behavior: Optional[Dict[str, Any]] = None,
        conversation_tone: Optional[str] = None,
    ) -> PersonalizationProfile:
        """Updates user personalization profile and emits 'PersonalizationUpdated' event."""
        profile = self.get_personalization(user_id)

        if preferred_assistant_name is not None:
            profile.preferred_assistant_name = preferred_assistant_name
        if preferred_wake_word is not None:
            profile.preferred_wake_word = preferred_wake_word
        if communication_style is not None:
            profile.communication_style = communication_style
        if preferred_language is not None:
            profile.preferred_language = preferred_language
        if preferred_ai_model is not None:
            profile.preferred_ai_model = preferred_ai_model
        if favorite_topics is not None:
            profile.favorite_topics = favorite_topics
        if productivity_preferences is not None:
            profile.productivity_preferences = productivity_preferences
        if learning_preferences is not None:
            profile.learning_preferences = learning_preferences
        if coding_preferences is not None:
            profile.coding_preferences = coding_preferences
        if notification_behavior is not None:
            profile.notification_behavior = notification_behavior
        if conversation_tone is not None:
            profile.conversation_tone = conversation_tone

        saved = self.repository.save_profile(profile)
        self.event_bus.emit(
            "PersonalizationUpdated",
            user_id=user_id,
            assistant_name=saved.preferred_assistant_name,
            wake_word=saved.preferred_wake_word,
        )
        return saved

    def build_context_window(
        self, user_id: str, current_query: str, max_items: int = 10
    ) -> Dict[str, Any]:
        """Constructs working memory context payload for conversations."""
        return self.context_builder.build_context_window(user_id, current_query, max_items)

    def get_metrics(self) -> Dict[str, Any]:
        """Returns operational metrics summary."""
        return {
            "status": "online" if self._running else "stopped",
            "phase": "P1.2",
            "subsystem": "ProductLayer.Memory",
        }

    def get_health(self) -> Dict[str, Any]:
        """Returns health status."""
        return {
            "healthy": self._running,
            "subsystem": "ProductLayer.Memory",
            "phase": "P1.2",
        }


# Global singleton instance
memory_engine = MemoryEngine()
