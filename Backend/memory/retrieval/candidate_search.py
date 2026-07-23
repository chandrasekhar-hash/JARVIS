import re
from typing import List, Dict, Any, Optional, Set
from memory.models.memory import Memory
from memory.models.query import MemoryQuery, MemoryResult
from memory.storage.base import BaseMemoryStorageProvider, BaseVectorStorageProvider
from memory.manager import memory_manager, MemoryManager
from tools.telemetry import log_structured, backend_log


class CandidateSearchEngine:
    """
    Retrieves and deduplicates memory candidates from Relational and Vector storage providers
    before ranking and filtering.
    """

    def __init__(
        self,
        memory_storage: Optional[BaseMemoryStorageProvider] = None,
        vector_storage: Optional[BaseVectorStorageProvider] = None
    ):
        self.memory_storage = memory_storage or memory_manager._storage
        self.vector_storage = vector_storage

    async def search_relational(self, query: MemoryQuery) -> List[MemoryResult]:
        """Performs keyword & tag candidate search against the relational memory provider."""
        all_memories = await self.memory_storage.list_memories(limit=1000)
        matched_results = []
        
        query_words = set(re.findall(r"\w+", query.query_text.lower())) if query.query_text else set()

        for mem in all_memories:
            # Filter by memory types if specified
            if query.types and mem.type not in query.types:
                continue

            # Filter by tags if specified
            if query.tags and not any(t in mem.metadata.tags for t in query.tags):
                continue

            # Text Keyword Match Scoring
            match_score = 0.5  # Baseline score for list match
            if query_words:
                content_words = set(re.findall(r"\w+", (mem.title + " " + mem.content).lower()))
                overlap = query_words.intersection(content_words)
                if overlap:
                    match_score = min(1.0, 0.5 + 0.5 * (len(overlap) / max(1, len(query_words))))
                else:
                    match_score = 0.3  # Low keyword overlap

            matched_results.append(
                MemoryResult(
                    memory=mem,
                    score=round(match_score, 4),
                    matched_by="relational_keyword"
                )
            )

        return matched_results

    async def search_vector(self, query_vector: List[float], top_k: int = 10) -> List[MemoryResult]:
        """Performs cosine vector similarity candidate search against the vector storage provider."""
        if not self.vector_storage or not query_vector:
            return []

        vector_hits = await self.vector_storage.search_vectors(query_vector, top_k=top_k)
        results = []
        
        for hit in vector_hits:
            mem_id = hit.get("memory_id")
            if not mem_id:
                continue
            mem = await self.memory_storage.get_memory(mem_id)
            if mem:
                results.append(
                    MemoryResult(
                        memory=mem,
                        score=float(hit.get("score", 0.5)),
                        matched_by="vector_distance"
                    )
                )

        return results

    async def retrieve_candidates(
        self,
        query: MemoryQuery,
        query_vector: Optional[List[float]] = None
    ) -> List[MemoryResult]:
        """
        Executes relational and vector searches, merging and deduplicating candidate memories.
        """
        # 1. Relational search
        relational_candidates = await self.search_relational(query)

        # 2. Vector search (if vector storage and query vector provided)
        vector_candidates = await self.search_vector(query_vector, top_k=query.top_k * 2) if query_vector else []

        # 3. Merge & Deduplicate
        candidate_map: Dict[str, MemoryResult] = {}

        for res in relational_candidates:
            candidate_map[res.memory.memory_id] = res

        for res in vector_candidates:
            mem_id = res.memory.memory_id
            if mem_id in candidate_map:
                # Retain higher similarity score and note hybrid match
                existing = candidate_map[mem_id]
                if res.score > existing.score:
                    existing.score = res.score
                existing.matched_by = "hybrid"
            else:
                candidate_map[mem_id] = res

        candidates = list(candidate_map.values())
        log_structured(backend_log, "INFO", f"[CandidateSearchEngine] Retrieved {len(candidates)} candidate memories for query '{query.query_text[:30]}'")
        return candidates
