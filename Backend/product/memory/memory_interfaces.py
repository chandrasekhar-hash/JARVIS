"""
Abstract Interfaces for Phase P1.2 (Memory & Personalization).
Adheres strictly to SOLID principles and Dependency Injection standards.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple, Dict, Any
from .memory_models import (
    Memory,
    MemoryCategory,
    MemoryType,
    MemoryStatus,
    MemoryCollection,
    MemorySettings,
    PersonalizationProfile,
    MemorySearchResult,
)


class IMemoryRepository(ABC):
    """Abstract Repository Interface for Memory persistence and user data isolation."""

    @abstractmethod
    def create_memory(self, memory: Memory) -> Memory:
        """Persists a new Memory record."""
        pass

    @abstractmethod
    def get_memory_by_id(self, user_id: str, memory_id: str) -> Optional[Memory]:
        """Retrieves a Memory record by user ID and memory ID."""
        pass

    @abstractmethod
    def update_memory(self, memory: Memory) -> Memory:
        """Updates an existing Memory record."""
        pass

    @abstractmethod
    def delete_memory(self, user_id: str, memory_id: str) -> bool:
        """Deletes a Memory record by memory ID."""
        pass

    @abstractmethod
    def archive_memory(self, user_id: str, memory_id: str) -> bool:
        """Archives a Memory record."""
        pass

    @abstractmethod
    def restore_memory(self, user_id: str, memory_id: str) -> bool:
        """Restores an archived Memory record."""
        pass

    @abstractmethod
    def supersede_memory(self, user_id: str, old_memory_id: str, new_memory: Memory) -> Tuple[Optional[Memory], Memory]:
        """Marks old memory as SUPERSEDED by new_memory and increments versioning."""
        pass

    @abstractmethod
    def reinforce_confidence(self, user_id: str, memory_id: str, boost: float = 0.05) -> Optional[Memory]:
        """Increments confidence_score and access_count for a memory."""
        pass

    @abstractmethod
    def list_memories(
        self,
        user_id: str,
        category: Optional[MemoryCategory] = None,
        memory_type: Optional[MemoryType] = None,
        status: Optional[MemoryStatus] = MemoryStatus.ACTIVE,
        collection_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Memory]:
        """Lists memories matching specified filters for a user ID."""
        pass

    @abstractmethod
    def pin_memory(self, user_id: str, memory_id: str) -> bool:
        """Pins a memory record."""
        pass

    @abstractmethod
    def unpin_memory(self, user_id: str, memory_id: str) -> bool:
        """Unpins a memory record."""
        pass

    @abstractmethod
    def clear_user_memories(self, user_id: str) -> int:
        """Clears all memories belonging to a user ID."""
        pass

    @abstractmethod
    def evict_expired_memories(self, user_id: str) -> int:
        """Purges expired memories based on retention policy and expires_at timestamp."""
        pass


class IPersonalizationRepository(ABC):
    """Abstract Repository Interface for PersonalizationProfile persistence."""

    @abstractmethod
    def get_profile(self, user_id: str) -> Optional[PersonalizationProfile]:
        """Retrieves PersonalizationProfile by user ID."""
        pass

    @abstractmethod
    def save_profile(self, profile: PersonalizationProfile) -> PersonalizationProfile:
        """Persists or updates PersonalizationProfile."""
        pass


class IMemorySettingsRepository(ABC):
    """Abstract Repository Interface for MemorySettings privacy toggles."""

    @abstractmethod
    def get_settings(self, user_id: str) -> MemorySettings:
        """Retrieves MemorySettings for user ID."""
        pass

    @abstractmethod
    def save_settings(self, settings: MemorySettings) -> MemorySettings:
        """Saves MemorySettings for user ID."""
        pass


class IMemorySearchEngine(ABC):
    """Abstract Search Engine Interface for hybrid indexing & retrieval."""

    @abstractmethod
    def search_memories(
        self,
        user_id: str,
        query: str,
        category: Optional[MemoryCategory] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20,
    ) -> MemorySearchResult:
        """Performs hybrid non-vector search across user memories."""
        pass


class IMemorySummarizer(ABC):
    """Abstract Interface for memory summarization, merging, and splitting."""

    @abstractmethod
    def summarize_memories(self, memories: List[Memory]) -> str:
        """Generates a concise summary text across a set of memories."""
        pass

    @abstractmethod
    def merge_memories(self, user_id: str, memories: List[Memory], merged_title: str) -> Memory:
        """Merges multiple memories into a consolidated Memory record."""
        pass

    @abstractmethod
    def split_memory(self, user_id: str, memory_id: str, split_delimiter: str = "\n\n") -> List[Memory]:
        """Splits a single memory into multiple sub-memories."""
        pass


class IMemoryContextBuilder(ABC):
    """Abstract Interface for constructing working memory context windows for conversations."""

    @abstractmethod
    def build_context_window(
        self, user_id: str, current_query: str, max_items: int = 10
    ) -> Dict[str, Any]:
        """Constructs memory context payload for Conversation Engine and Voice Orchestrator."""
        pass
