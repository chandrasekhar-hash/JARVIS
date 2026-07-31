"""
JARVIS Product 1.6 - Retrieval Pipeline.
Orchestrates permission filtering, hybrid search execution, chunk fetching, and re-ranking.
"""

import time
from typing import List, Dict, Any, Optional
from .interfaces import IMetadataStore
from .models import Chunk, Document
from .permissions import KnowledgePermissionEngine
from .search import HybridSearchEngine, ReRankerEngine
from .telemetry import knowledge_telemetry
from .logging import knowledge_logger


class RetrievalPipeline:
    def __init__(
        self,
        metadata_store: IMetadataStore,
        hybrid_search_engine: HybridSearchEngine,
        reranker: Optional[ReRankerEngine] = None,
    ):
        self.metadata_store = metadata_store
        self.hybrid_search_engine = hybrid_search_engine
        self.reranker = reranker or ReRankerEngine()

    def retrieve(
        self,
        query: str,
        user_id: str,
        top_k: int = 10,
        user_roles: Optional[List[str]] = None,
        plugin_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        start_time = time.time()
        knowledge_telemetry.record_query()

        # 1. Fetch user accessible documents
        all_docs = self.metadata_store.list_documents(limit=500)
        allowed_doc_ids = KnowledgePermissionEngine.filter_accessible_document_ids(
            documents=all_docs,
            user_id=user_id,
            user_roles=user_roles,
            plugin_id=plugin_id,
        )

        if not allowed_doc_ids:
            return []

        # 2. Execute Hybrid Search (Dense + Sparse RRF)
        candidate_pairs = self.hybrid_search_engine.search(
            query=query,
            top_k=top_k * 2,
            allowed_doc_ids=allowed_doc_ids,
        )

        if not candidate_pairs:
            return []

        chunk_ids = [chk_id for chk_id, _ in candidate_pairs]
        scores_map = {chk_id: score for chk_id, score in candidate_pairs}

        # 3. Retrieve Chunk metadata
        chunks = self.metadata_store.get_chunks_by_ids(chunk_ids)
        scores = [scores_map.get(chk.chunk_id, 0.0) for chk in chunks]

        # 4. Apply Re-Ranker
        reranked_pairs = self.reranker.rerank(query, chunks, scores, top_k=top_k)

        # 5. Format results with citations
        results: List[Dict[str, Any]] = []
        doc_cache: Dict[str, Document] = {}

        for chk, score in reranked_pairs:
            if chk.document_id not in doc_cache:
                doc_obj = self.metadata_store.get_document(chk.document_id)
                if doc_obj:
                    doc_cache[chk.document_id] = doc_obj

            doc_title = doc_cache[chk.document_id].title if chk.document_id in doc_cache else "Unknown Document"

            results.append({
                "chunk_id": chk.chunk_id,
                "document_id": chk.document_id,
                "document_title": doc_title,
                "text": chk.text,
                "score": round(score, 4),
                "location": chk.location.to_dict(),
                "citation": f'[Doc: "{doc_title}", Chunk: {chk.chunk_id}]',
            })

        duration = (time.time() - start_time) * 1000.0
        knowledge_logger.log_event(
            event_name="RETRIEVAL_SUCCESS",
            user_id=user_id,
            details={"query": query, "results_count": len(results)},
            duration_ms=duration,
        )

        return results
