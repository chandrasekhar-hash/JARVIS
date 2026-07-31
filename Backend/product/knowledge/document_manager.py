"""
JARVIS Product 1.6 - Document Manager.
Orchestrates document CRUD operations, status management, re-indexing, and cascading deletions.
"""

import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from .interfaces import IMetadataStore, IVectorStore
from .models import Document, Chunk, DocumentStatus, DocumentPermissions
from .ingestion import IngestionPipeline
from .embedding import EmbeddingCache
from .telemetry import knowledge_telemetry
from .logging import knowledge_logger

logger = logging.getLogger(__name__)


class DocumentManager:
    def __init__(
        self,
        metadata_store: IMetadataStore,
        vector_store: IVectorStore,
        embedding_cache: EmbeddingCache,
        ingestion_pipeline: Optional[IngestionPipeline] = None,
    ):
        self.metadata_store = metadata_store
        self.vector_store = vector_store
        self.embedding_cache = embedding_cache
        self.ingestion_pipeline = ingestion_pipeline or IngestionPipeline()

    def ingest_document(
        self,
        file_path: str,
        title: str,
        owner_id: str,
        tags: Optional[List[str]] = None,
        permissions: Optional[DocumentPermissions] = None,
    ) -> Document:
        start_time = time.time()

        # Process file & chunk
        doc, chunks = self.ingestion_pipeline.process_file(
            file_path=file_path,
            title=title,
            owner_id=owner_id,
            tags=tags,
            permissions=permissions,
        )

        doc.status = DocumentStatus.PROCESSING
        self.metadata_store.save_document(doc)

        try:
            # Generate Embeddings for Chunks
            chunk_texts = [c.text for c in chunks]
            embeddings, hits = self.embedding_cache.get_embeddings(chunk_texts)
            knowledge_telemetry.record_embedding(len(chunk_texts), hits)

            chunk_ids = []
            vectors = []
            metadatas = []

            for chk, emb in zip(chunks, embeddings):
                chk.embedding = emb
                chunk_ids.append(chk.chunk_id)
                vectors.append(emb)
                metadatas.append({
                    "document_id": doc.document_id,
                    "chunk_index": chk.chunk_index,
                    "checksum": chk.checksum,
                })

            # Save Chunks & Vectors
            self.metadata_store.save_chunks(chunks)
            self.vector_store.add_vectors(chunk_ids, vectors, metadatas)

            doc.status = DocumentStatus.INDEXED
            self.metadata_store.save_document(doc)

            knowledge_telemetry.record_ingestion(len(chunks))
            duration = (time.time() - start_time) * 1000.0
            knowledge_logger.log_event(
                event_name="DOCUMENT_INGESTION_SUCCESS",
                user_id=owner_id,
                document_id=doc.document_id,
                details={"title": doc.title, "chunks": len(chunks)},
                duration_ms=duration,
            )

            return doc

        except Exception as e:
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(e)
            self.metadata_store.save_document(doc)
            logger.error(f"Ingestion failed for {doc.document_id}: {e}")
            raise e

    def get_document(self, document_id: str) -> Optional[Document]:
        return self.metadata_store.get_document(document_id)

    def list_documents(self, owner_id: Optional[str] = None, limit: int = 100) -> List[Document]:
        return self.metadata_store.list_documents(owner_id=owner_id, limit=limit)

    def delete_document(self, document_id: str, user_id: str) -> bool:
        start_time = time.time()
        doc = self.metadata_store.get_document(document_id)
        if not doc:
            return False

        # Cascading deletion across vector store & metadata store
        self.vector_store.delete_document_vectors(document_id)
        self.metadata_store.delete_document(document_id)

        duration = (time.time() - start_time) * 1000.0
        knowledge_logger.log_event(
            event_name="DOCUMENT_DELETED",
            user_id=user_id,
            document_id=document_id,
            duration_ms=duration,
        )
        return True

    def reindex_document(self, document_id: str, user_id: str) -> bool:
        doc = self.metadata_store.get_document(document_id)
        if not doc or not doc.source:
            return False

        # Remove existing chunks & vectors
        self.vector_store.delete_document_vectors(document_id)
        self.metadata_store.delete_chunks_by_document(document_id)

        # Re-ingest
        self.ingest_document(
            file_path=doc.source,
            title=doc.title,
            owner_id=doc.owner,
            tags=doc.tags,
            permissions=doc.permissions,
        )
        return True
