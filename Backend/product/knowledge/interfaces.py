"""
JARVIS Product 1.6 - Knowledge Engine Interfaces.

Defines abstract contracts for Document Management, Ingestion, Parsing, OCR, Chunking, Embedding, Vector Storage, Metadata Storage, Search Engines, and RAG Coordinators.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from .models import Document, Chunk, DocumentPermissions, DocumentType, DocumentStatus


class IParser(ABC):
    @abstractmethod
    def can_parse(self, source: str, mime_type: Optional[str] = None) -> bool:
        pass

    @abstractmethod
    def parse(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Returns extracted raw text and extracted document metadata."""
        pass


class IOCREngine(ABC):
    @abstractmethod
    def extract_text_from_image(self, image_path: str) -> Tuple[str, float]:
        """Returns extracted text and confidence score (0.0 to 1.0)."""
        pass


class IChunker(ABC):
    @abstractmethod
    def chunk_text(
        self,
        document_id: str,
        text: str,
        chunk_size: int = 512,
        overlap: int = 64,
        section_title: Optional[str] = None,
    ) -> List[Chunk]:
        pass


class IEmbeddingProvider(ABC):
    @abstractmethod
    def get_provider_name(self) -> str:
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        pass

    @abstractmethod
    def get_model_version(self) -> str:
        pass

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        pass


class IVectorStore(ABC):
    @abstractmethod
    def initialize(self) -> None:
        pass

    @abstractmethod
    def add_vectors(
        self,
        chunk_ids: List[str],
        vectors: List[List[float]],
        metadatas: List[Dict[str, Any]],
    ) -> bool:
        pass

    @abstractmethod
    def search_vectors(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[str, float]]:
        """Returns List of (chunk_id, similarity_score)."""
        pass

    @abstractmethod
    def delete_vectors(self, chunk_ids: List[str]) -> bool:
        pass

    @abstractmethod
    def delete_document_vectors(self, document_id: str) -> bool:
        pass


class IMetadataStore(ABC):
    @abstractmethod
    def initialize(self) -> None:
        pass

    @abstractmethod
    def save_document(self, document: Document) -> bool:
        pass

    @abstractmethod
    def get_document(self, document_id: str) -> Optional[Document]:
        pass

    @abstractmethod
    def list_documents(
        self,
        owner_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Document]:
        pass

    @abstractmethod
    def delete_document(self, document_id: str) -> bool:
        pass

    @abstractmethod
    def save_chunks(self, chunks: List[Chunk]) -> bool:
        pass

    @abstractmethod
    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        pass

    @abstractmethod
    def get_chunks_by_document(self, document_id: str) -> List[Chunk]:
        pass

    @abstractmethod
    def get_chunks_by_ids(self, chunk_ids: List[str]) -> List[Chunk]:
        pass

    @abstractmethod
    def delete_chunks_by_document(self, document_id: str) -> bool:
        pass

    @abstractmethod
    def search_fts5_keywords(
        self,
        query: str,
        top_k: int = 10,
        allowed_doc_ids: Optional[List[str]] = None,
    ) -> List[Tuple[str, float]]:
        """Returns List of (chunk_id, bm25_score)."""
        pass


class ISearchEngine(ABC):
    @abstractmethod
    def search(
        self,
        query: str,
        user_id: str,
        top_k: int = 10,
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Returns ranked list of chunk search result dictionaries with citations."""
        pass


class IRAGCoordinator(ABC):
    @abstractmethod
    def query(
        self,
        user_query: str,
        user_id: str,
        top_k: int = 5,
        max_context_tokens: int = 3000,
    ) -> Dict[str, Any]:
        """Returns grounded response payload with answer, citations, and metadata."""
        pass
