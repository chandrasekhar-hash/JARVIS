"""
JARVIS Product 1.6 - Knowledge Engine Domain Models.

Defines core data classes and enums for Documents, Chunks, Locations, Permissions, and Statuses.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
import uuid


class DocumentStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    INDEXED = "INDEXED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class DocumentType(str, Enum):
    PDF = "PDF"
    DOCX = "DOCX"
    TXT = "TXT"
    MARKDOWN = "MARKDOWN"
    HTML = "HTML"
    CODE = "CODE"
    IMAGE_OCR = "IMAGE_OCR"
    NOTE = "NOTE"


@dataclass
class DocumentPermissions:
    owner_id: str
    is_public: bool = False
    allowed_roles: List[str] = field(default_factory=lambda: ["admin", "user"])
    allowed_users: List[str] = field(default_factory=list)
    allowed_plugins: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "owner_id": self.owner_id,
            "is_public": self.is_public,
            "allowed_roles": self.allowed_roles,
            "allowed_users": self.allowed_users,
            "allowed_plugins": self.allowed_plugins,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentPermissions":
        if not data:
            return cls(owner_id="system")
        return cls(
            owner_id=data.get("owner_id", "system"),
            is_public=data.get("is_public", False),
            allowed_roles=data.get("allowed_roles", ["admin", "user"]),
            allowed_users=data.get("allowed_users", []),
            allowed_plugins=data.get("allowed_plugins", []),
        )


@dataclass
class Document:
    document_id: str
    title: str
    owner: str
    source: str
    document_type: DocumentType
    language: str = "en"
    checksum: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    tags: List[str] = field(default_factory=list)
    permissions: DocumentPermissions = field(default_factory=lambda: DocumentPermissions(owner_id="system"))
    embedding_version: str = "all-MiniLM-L6-v2:v1"
    index_version: str = "v1.6.0"
    status: DocumentStatus = DocumentStatus.PENDING
    file_size_bytes: int = 0
    total_chunks: int = 0
    error_message: Optional[str] = None
    custom_metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create_new(
        cls,
        title: str,
        owner: str,
        source: str,
        document_type: DocumentType,
        checksum: str,
        tags: Optional[List[str]] = None,
        permissions: Optional[DocumentPermissions] = None,
        file_size_bytes: int = 0,
        custom_metadata: Optional[Dict[str, Any]] = None,
    ) -> "Document":
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow()
        return cls(
            document_id=doc_id,
            title=title,
            owner=owner,
            source=source,
            document_type=document_type,
            checksum=checksum,
            created_at=now,
            updated_at=now,
            tags=tags or [],
            permissions=permissions or DocumentPermissions(owner_id=owner),
            file_size_bytes=file_size_bytes,
            custom_metadata=custom_metadata or {},
        )


@dataclass
class ChunkLocation:
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    start_offset: int = 0
    end_offset: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "section_title": self.section_title,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChunkLocation":
        if not data:
            return cls()
        return cls(
            page_number=data.get("page_number"),
            section_title=data.get("section_title"),
            start_offset=data.get("start_offset", 0),
            end_offset=data.get("end_offset", 0),
        )


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    chunk_index: int
    text: str
    token_count: int
    location: ChunkLocation
    checksum: str
    embedding: Optional[List[float]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create_new(
        cls,
        document_id: str,
        chunk_index: int,
        text: str,
        token_count: int,
        location: ChunkLocation,
        checksum: str,
        embedding: Optional[List[float]] = None,
    ) -> "Chunk":
        chk_id = f"chk_{uuid.uuid4().hex[:12]}"
        return cls(
            chunk_id=chk_id,
            document_id=document_id,
            chunk_index=chunk_index,
            text=text,
            token_count=token_count,
            location=location,
            checksum=checksum,
            embedding=embedding,
        )
