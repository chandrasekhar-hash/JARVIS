"""
J.A.R.V.I.S. Product 1.6 - Knowledge Engine Package Initialization.
Exports Knowledge Manager, Document Manager, Models, Interfaces, Pipelines, Search, and Tools.
"""

from .models import (
    Document,
    DocumentStatus,
    DocumentType,
    DocumentPermissions,
    Chunk,
    ChunkLocation,
)
from .interfaces import (
    IParser,
    IOCREngine,
    IChunker,
    IEmbeddingProvider,
    IVectorStore,
    IMetadataStore,
    ISearchEngine,
    IRAGCoordinator,
)
from .document_manager import DocumentManager
from .ingestion import IngestionPipeline, FileValidator, TextNormalizer
from .chunking import ChunkingEngine
from .embedding import (
    LocalSTEmbeddingProvider,
    OpenAIEmbeddingProvider,
    EmbeddingProviderFactory,
    EmbeddingCache,
)
from .storage import (
    VectorStoreBase,
    SQLiteVectorStore,
    FAISSVectorStore,
    SQLiteMetadataStore,
)
from .search import (
    SemanticSearchEngine,
    KeywordSearchEngine,
    HybridSearchEngine,
    ReRankerEngine,
)
from .retrieval import RetrievalPipeline
from .rag import RAGCoordinator, ContextBuilder, HallucinationGuard
from .permissions import KnowledgePermissionEngine
from .telemetry import KnowledgeTelemetry, knowledge_telemetry
from .logging import KnowledgeLogger, knowledge_logger
from .knowledge_engine import KnowledgeManager, knowledge_manager_instance
from .tools import (
    handle_knowledge_ingest,
    handle_knowledge_search,
    handle_knowledge_query_rag,
    handle_knowledge_delete,
    handle_knowledge_reindex,
    get_knowledge_tool_metadatas,
)

__all__ = [
    "Document",
    "DocumentStatus",
    "DocumentType",
    "DocumentPermissions",
    "Chunk",
    "ChunkLocation",
    "IParser",
    "IOCREngine",
    "IChunker",
    "IEmbeddingProvider",
    "IVectorStore",
    "IMetadataStore",
    "ISearchEngine",
    "IRAGCoordinator",
    "DocumentManager",
    "IngestionPipeline",
    "FileValidator",
    "TextNormalizer",
    "ChunkingEngine",
    "LocalSTEmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "EmbeddingProviderFactory",
    "EmbeddingCache",
    "VectorStoreBase",
    "SQLiteVectorStore",
    "FAISSVectorStore",
    "SQLiteMetadataStore",
    "SemanticSearchEngine",
    "KeywordSearchEngine",
    "HybridSearchEngine",
    "ReRankerEngine",
    "RetrievalPipeline",
    "RAGCoordinator",
    "ContextBuilder",
    "HallucinationGuard",
    "KnowledgePermissionEngine",
    "KnowledgeTelemetry",
    "knowledge_telemetry",
    "KnowledgeLogger",
    "knowledge_logger",
    "KnowledgeManager",
    "knowledge_manager_instance",
    "handle_knowledge_ingest",
    "handle_knowledge_search",
    "handle_knowledge_query_rag",
    "handle_knowledge_delete",
    "handle_knowledge_reindex",
    "get_knowledge_tool_metadatas",
]
