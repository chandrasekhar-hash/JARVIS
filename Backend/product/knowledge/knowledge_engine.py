"""
JARVIS Product 1.6 - Master Knowledge Engine Entrypoint.
Initializes storage engines, search pipelines, RAG coordinators, and document management APIs.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from .storage import SQLiteMetadataStore, SQLiteVectorStore
from .embedding import LocalSTEmbeddingProvider, EmbeddingCache, EmbeddingProviderFactory
from .search import SemanticSearchEngine, KeywordSearchEngine, HybridSearchEngine, ReRankerEngine
from .retrieval import RetrievalPipeline
from .rag import RAGCoordinator
from .document_manager import DocumentManager
from .models import Document, DocumentPermissions
from .telemetry import knowledge_telemetry

logger = logging.getLogger(__name__)


class KnowledgeManager:
    def __init__(self, db_path: str = "logs/jarvis_knowledge.db"):
        self.db_path = db_path

        # 1. Storage Layers
        self.metadata_store = SQLiteMetadataStore(db_path=db_path)
        self.vector_store = SQLiteVectorStore(db_path=db_path)

        # 2. Embedding Subsystem
        self.provider = EmbeddingProviderFactory.get_provider("local")
        self.embedding_cache = EmbeddingCache(provider=self.provider)

        # 3. Search Engines
        self.semantic_search = SemanticSearchEngine(
            vector_store=self.vector_store,
            embedding_cache=self.embedding_cache,
        )
        self.keyword_search = KeywordSearchEngine(metadata_store=self.metadata_store)
        self.hybrid_search = HybridSearchEngine(
            semantic_engine=self.semantic_search,
            keyword_engine=self.keyword_search,
        )
        self.reranker = ReRankerEngine()

        # 4. Pipelines & Coordinators
        self.retrieval_pipeline = RetrievalPipeline(
            metadata_store=self.metadata_store,
            hybrid_search_engine=self.hybrid_search,
            reranker=self.reranker,
        )
        self.rag_coordinator = RAGCoordinator(retrieval_pipeline=self.retrieval_pipeline)

        # 5. Document Management
        self.document_manager = DocumentManager(
            metadata_store=self.metadata_store,
            vector_store=self.vector_store,
            embedding_cache=self.embedding_cache,
        )

        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return

        # Ensure directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        self.metadata_store.initialize()
        self.vector_store.initialize()
        self._initialized = True
        logger.info("JARVIS Knowledge Engine Product 1.6 initialized successfully.")

    # High-level API Methods
    def ingest_document(
        self,
        file_path: str,
        title: str,
        owner_id: str,
        tags: Optional[List[str]] = None,
        permissions: Optional[DocumentPermissions] = None,
    ) -> Document:
        self.initialize()
        return self.document_manager.ingest_document(
            file_path=file_path,
            title=title,
            owner_id=owner_id,
            tags=tags,
            permissions=permissions,
        )

    def search_knowledge(
        self,
        query: str,
        user_id: str,
        top_k: int = 10,
        user_roles: Optional[List[str]] = None,
        plugin_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        self.initialize()
        return self.retrieval_pipeline.retrieve(
            query=query,
            user_id=user_id,
            top_k=top_k,
            user_roles=user_roles,
            plugin_id=plugin_id,
        )

    def query_rag(
        self,
        user_query: str,
        user_id: str,
        top_k: int = 5,
        max_context_tokens: int = 3000,
        user_roles: Optional[List[str]] = None,
        plugin_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        self.initialize()
        return self.rag_coordinator.query(
            user_query=user_query,
            user_id=user_id,
            top_k=top_k,
            max_context_tokens=max_context_tokens,
            user_roles=user_roles,
            plugin_id=plugin_id,
        )

    def delete_document(self, document_id: str, user_id: str) -> bool:
        self.initialize()
        return self.document_manager.delete_document(document_id=document_id, user_id=user_id)

    def reindex_document(self, document_id: str, user_id: str) -> bool:
        self.initialize()
        return self.document_manager.reindex_document(document_id=document_id, user_id=user_id)

    def list_documents(self, owner_id: Optional[str] = None) -> List[Document]:
        self.initialize()
        return self.document_manager.list_documents(owner_id=owner_id)

    def get_telemetry_metrics(self) -> Dict[str, Any]:
        return knowledge_telemetry.get_metrics()


knowledge_manager_instance = KnowledgeManager()
