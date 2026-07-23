from typing import Optional, List, Dict, Any
from brain.event_bus import event_bus
from memory.models.query import MemoryQuery, MemoryResult
from memory.retrieval.candidate_search import CandidateSearchEngine
from memory.retrieval.ranker import MemoryRanker, RankingWeights
from memory.retrieval.filter import MemoryFilter
from memory.retrieval.context_generator import MemoryContextGenerator, MemoryContextPackage
from tools.telemetry import log_structured, backend_log


class RetrievalPipeline:
    """
    Orchestrates the Memory Retrieval Engine stages following Phase 4 architecture:
    Candidate Search -> Ranking -> Filtering -> Context Generation.
    """

    def __init__(
        self,
        search_engine: Optional[CandidateSearchEngine] = None,
        ranker: Optional[MemoryRanker] = None,
        filter_engine: Optional[MemoryFilter] = None,
        context_generator: Optional[MemoryContextGenerator] = None
    ):
        self.search_engine = search_engine or CandidateSearchEngine()
        self.ranker = ranker or MemoryRanker()
        self.filter_engine = filter_engine or MemoryFilter()
        self.context_generator = context_generator or MemoryContextGenerator()

    async def execute(
        self,
        query: MemoryQuery,
        query_vector: Optional[List[float]] = None
    ) -> MemoryContextPackage:
        """
        Executes the complete retrieval pipeline for a given MemoryQuery and optional vector query.
        Returns a structured MemoryContextPackage.
        """
        # 1. CANDIDATE SEARCH STAGE
        candidates: List[MemoryResult] = await self.search_engine.retrieve_candidates(query, query_vector)
        event_bus.emit("MemoryRetrieved", query_text=query.query_text, candidate_count=len(candidates))

        if not candidates:
            log_structured(backend_log, "INFO", f"[RetrievalPipeline] No candidates retrieved for query '{query.query_text}'")
            return MemoryContextPackage(has_context=False, memory_count=0, formatted_context="", retrieved_memories=[])

        # 2. RANKING STAGE
        ranked_candidates: List[MemoryResult] = self.ranker.rank(candidates)
        event_bus.emit("CandidatesRanked", top_score=ranked_candidates[0].score if ranked_candidates else 0.0)

        # 3. FILTERING STAGE
        filtered_candidates: List[MemoryResult] = self.filter_engine.filter(ranked_candidates)
        event_bus.emit("CandidatesFiltered", retained_count=len(filtered_candidates), original_count=len(ranked_candidates))

        # 4. CONTEXT GENERATION STAGE
        context_package: MemoryContextPackage = self.context_generator.generate(filtered_candidates)
        event_bus.emit(
            "ContextGenerated",
            has_context=context_package.has_context,
            memory_count=context_package.memory_count
        )

        log_structured(
            backend_log,
            "INFO",
            f"[RetrievalPipeline] Retrieval execution complete. Context package generated with {context_package.memory_count} memories."
        )
        return context_package


# Singleton instance of RetrievalPipeline
retrieval_pipeline = RetrievalPipeline()
