"""
Data Models and Domain Entities for Phase P1.2 (Memory & Personalization).
Includes Memory Categories, Types, Status, Retention Policies, Personalization Profiles, and Serialization methods.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
import time


class MemoryCategory(str, Enum):
    """Broad category separating user memory from saved knowledge."""
    USER_MEMORY = "USER_MEMORY"
    KNOWLEDGE = "KNOWLEDGE"


class MemoryType(str, Enum):
    """Specific functional type of memory entity."""
    CONVERSATION = "CONVERSATION"
    LONG_TERM = "LONG_TERM"
    WORKING = "WORKING"
    CUSTOM = "CUSTOM"


class MemoryStatus(str, Enum):
    """Operational lifecycle status of memory entity."""
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    SUPERSEDED = "SUPERSEDED"
    DELETED = "DELETED"


class ImportanceLevel(str, Enum):
    """Importance classification level."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RetentionPolicy(str, Enum):
    """Retention policy defining memory expiration lifecycle."""
    PERMANENT = "PERMANENT"
    SESSION_ONLY = "SESSION_ONLY"
    THIRTY_DAYS = "THIRTY_DAYS"
    NINETY_DAYS = "NINETY_DAYS"
    MANUAL_ONLY = "MANUAL_ONLY"


@dataclass
class Memory:
    """Primary Memory entity record."""
    memory_id: str
    user_id: str
    category: MemoryCategory = MemoryCategory.USER_MEMORY
    type: MemoryType = MemoryType.LONG_TERM
    title: str = ""
    content: str = ""
    embedding_placeholder: Optional[List[float]] = None
    tags: List[str] = field(default_factory=list)
    importance_score: float = 0.5  # 0.0 to 1.0
    confidence_score: float = 0.6  # 0.0 to 1.0 (evolves dynamically)
    is_pinned: bool = False
    retention_policy: RetentionPolicy = RetentionPolicy.PERMANENT
    expires_at: Optional[float] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 1
    reinforcement_count: int = 1
    source: str = "user_input"
    status: MemoryStatus = MemoryStatus.ACTIVE
    version: int = 1
    superseded_by: Optional[str] = None
    collection_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        """Checks if memory has passed its expiration timestamp."""
        if not self.expires_at:
            return False
        now = current_time if current_time is not None else time.time()
        return now >= self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Serializes memory entity into dictionary format."""
        return {
            "memory_id": self.memory_id,
            "user_id": self.user_id,
            "category": self.category.value if isinstance(self.category, MemoryCategory) else str(self.category),
            "type": self.type.value if isinstance(self.type, MemoryType) else str(self.type),
            "title": self.title,
            "content": self.content,
            "embedding_placeholder": self.embedding_placeholder,
            "tags": self.tags,
            "importance_score": self.importance_score,
            "confidence_score": self.confidence_score,
            "is_pinned": self.is_pinned,
            "retention_policy": self.retention_policy.value if isinstance(self.retention_policy, RetentionPolicy) else str(self.retention_policy),
            "expires_at": self.expires_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "reinforcement_count": self.reinforcement_count,
            "source": self.source,
            "status": self.status.value if isinstance(self.status, MemoryStatus) else str(self.status),
            "version": self.version,
            "superseded_by": self.superseded_by,
            "collection_id": self.collection_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Memory":
        """Instantiates Memory entity from dictionary representation."""
        cat_str = data.get("category", "USER_MEMORY")
        type_str = data.get("type", "LONG_TERM")
        status_str = data.get("status", "ACTIVE")
        ret_str = data.get("retention_policy", "PERMANENT")

        return cls(
            memory_id=data.get("memory_id", ""),
            user_id=data.get("user_id", ""),
            category=MemoryCategory(cat_str) if cat_str in MemoryCategory.__members__ else MemoryCategory.USER_MEMORY,
            type=MemoryType(type_str) if type_str in MemoryType.__members__ else MemoryType.LONG_TERM,
            title=data.get("title", ""),
            content=data.get("content", ""),
            embedding_placeholder=data.get("embedding_placeholder"),
            tags=data.get("tags", []),
            importance_score=float(data.get("importance_score", 0.5)),
            confidence_score=float(data.get("confidence_score", 0.6)),
            is_pinned=bool(data.get("is_pinned", False)),
            retention_policy=RetentionPolicy(ret_str) if ret_str in RetentionPolicy.__members__ else RetentionPolicy.PERMANENT,
            expires_at=data.get("expires_at"),
            created_at=float(data.get("created_at", time.time())),
            updated_at=float(data.get("updated_at", time.time())),
            last_accessed=float(data.get("last_accessed", time.time())),
            access_count=int(data.get("access_count", 1)),
            reinforcement_count=int(data.get("reinforcement_count", 1)),
            source=data.get("source", "user_input"),
            status=MemoryStatus(status_str) if status_str in MemoryStatus.__members__ else MemoryStatus.ACTIVE,
            version=int(data.get("version", 1)),
            superseded_by=data.get("superseded_by"),
            collection_id=data.get("collection_id"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class MemoryTag:
    """Memory tag mapping entity."""
    tag_id: str
    memory_id: str
    tag_name: str
    created_at: float = field(default_factory=time.time)


@dataclass
class MemoryLink:
    """Relational link between two memories."""
    link_id: str
    source_memory_id: str
    target_memory_id: str
    relation_type: str = "related"
    created_at: float = field(default_factory=time.time)


@dataclass
class MemoryCollection:
    """User-created collection of pinned memories, bookmarks, or notes."""
    collection_id: str
    user_id: str
    name: str
    description: str = ""
    color: str = "#4A90E2"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "collection_id": self.collection_id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "color": self.color,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class MemorySettings:
    """User privacy and retention settings for Memory platform."""
    user_id: str
    memory_enabled: bool = True
    auto_summarize: bool = True
    max_working_memory_items: int = 10
    retention_days: int = 365
    privacy_opt_out: bool = False
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "memory_enabled": self.memory_enabled,
            "auto_summarize": self.auto_summarize,
            "max_working_memory_items": self.max_working_memory_items,
            "retention_days": self.retention_days,
            "privacy_opt_out": self.privacy_opt_out,
            "updated_at": self.updated_at,
        }


@dataclass
class PersonalizationProfile:
    """Personalization profile for customizing J.A.R.V.I.S. assistant interaction style."""
    user_id: str
    preferred_assistant_name: str = "J.A.R.V.I.S."
    preferred_wake_word: str = "JARVIS"
    communication_style: str = "concise_professional"
    preferred_language: str = "en-US"
    preferred_ai_model: str = "gemini-2.5-flash"
    favorite_topics: List[str] = field(default_factory=list)
    productivity_preferences: Dict[str, Any] = field(default_factory=dict)
    learning_preferences: Dict[str, Any] = field(default_factory=dict)
    coding_preferences: Dict[str, Any] = field(default_factory=dict)
    notification_behavior: Dict[str, Any] = field(default_factory=dict)
    conversation_tone: str = "helpful"
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "preferred_assistant_name": self.preferred_assistant_name,
            "preferred_wake_word": self.preferred_wake_word,
            "communication_style": self.communication_style,
            "preferred_language": self.preferred_language,
            "preferred_ai_model": self.preferred_ai_model,
            "favorite_topics": self.favorite_topics,
            "productivity_preferences": self.productivity_preferences,
            "learning_preferences": self.learning_preferences,
            "coding_preferences": self.coding_preferences,
            "notification_behavior": self.notification_behavior,
            "conversation_tone": self.conversation_tone,
            "updated_at": self.updated_at,
        }


@dataclass
class MemorySearchResult:
    """Container for hybrid search outputs."""
    memories: List[Memory]
    total_count: int
    query: str
    search_time_ms: float
