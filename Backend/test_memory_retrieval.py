import sys
import os
import time
import asyncio
from typing import List

# Ensure Backend directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from brain.event_bus import event_bus
from memory import (
    MemoryManager,
    Memory,
    MemoryType,
    MemoryMetadata,
    MemoryChunk,
    MemoryQuery,
    SQLiteMemoryStorageProvider,
    SQLiteVectorStorageProvider,
    InMemoryStorageProvider,
)
from memory.retrieval import (
    CandidateSearchEngine,
    MemoryRanker,
    RankingWeights,
    MemoryFilter,
    MemoryContextGenerator,
    RetrievalPipeline,
)

TEST_DB_PATH = "logs/test_retrieval_memory.db"


def cleanup_test_db():
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass


def section(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


async def test_candidate_search():
    section("1. CANDIDATE SEARCH ENGINE (RELATIONAL & VECTOR)")
    cleanup_test_db()

    mem_provider = SQLiteMemoryStorageProvider(db_path=TEST_DB_PATH)
    vec_provider = SQLiteVectorStorageProvider(db_path=TEST_DB_PATH)

    search_engine = CandidateSearchEngine(memory_storage=mem_provider, vector_storage=vec_provider)

    # 1. Store Test Memories
    m1 = Memory(
        memory_id="mem_code_theme",
        type=MemoryType.PREFERENCE,
        title="VS Code Theme Preference",
        content="The user prefers Dark Plus theme in Visual Studio Code.",
        metadata=MemoryMetadata(importance_score=8.5, tags=["editor", "theme"])
    )
    m2 = Memory(
        memory_id="mem_python_dev",
        type=MemoryType.PROJECT,
        title="JARVIS Backend Development",
        content="JARVIS backend is written in Python with FastAPI.",
        metadata=MemoryMetadata(importance_score=9.0, tags=["python", "jarvis"])
    )
    await mem_provider.store_memory(m1)
    await mem_provider.store_memory(m2)

    # Store Vector Embedding
    chunk1 = MemoryChunk(chunk_id="chunk_theme", memory_id="mem_code_theme", content=m1.content, embedding=[1.0, 0.0, 0.0])
    await vec_provider.add_vector(chunk1)

    # 2. Relational Query Search
    query = MemoryQuery(query_text="theme preference editor", top_k=5)
    candidates = await search_engine.search_relational(query)
    assert len(candidates) >= 1
    print(f"[PASS] Relational candidate search returned {len(candidates)} hits.")

    # 3. Vector Query Search
    vec_candidates = await search_engine.search_vector(query_vector=[0.9, 0.1, 0.0], top_k=2)
    assert len(vec_candidates) == 1
    assert vec_candidates[0].memory.memory_id == "mem_code_theme"
    print(f"[PASS] Vector candidate search matched memory: ID='{vec_candidates[0].memory.memory_id}' | Score={vec_candidates[0].score}")

    # 4. Merged Candidate Retrieval
    merged = await search_engine.retrieve_candidates(query, query_vector=[0.9, 0.1, 0.0])
    assert len(merged) == 2
    print(f"[PASS] Merged & deduplicated candidates count: {len(merged)}")


def test_ranking_algorithm():
    section("2. MULTI-FACTOR RANKING ALGORITHM")

    ranker = MemoryRanker(weights=RankingWeights(w_sim=0.40, w_rec=0.25, w_imp=0.15, w_freq=0.10, w_conf=0.10))

    now = time.time()

    # Memory 1: Recent, high importance
    m1 = Memory(
        memory_id="m1",
        type=MemoryType.PREFERENCE,
        title="High Importance Preference",
        content="User prefers dark theme",
        metadata=MemoryMetadata(importance_score=10.0, last_accessed=now, confidence=1.0, access_count=5)
    )

    # Memory 2: Old, low importance
    m2 = Memory(
        memory_id="m2",
        type=MemoryType.EPISODIC,
        title="Old Episodic Note",
        content="User checked weather 60 days ago",
        metadata=MemoryMetadata(importance_score=2.0, last_accessed=now - (60 * 86400), confidence=0.7, access_count=1)
    )

    from memory.models.query import MemoryResult
    cands = [
        MemoryResult(memory=m2, score=0.6, matched_by="keyword"),
        MemoryResult(memory=m1, score=0.8, matched_by="keyword")
    ]

    ranked = ranker.rank(cands, current_time=now)
    assert len(ranked) == 2
    assert ranked[0].memory.memory_id == "m1"
    assert ranked[0].score > ranked[1].score
    print(f"[PASS] Multi-factor ranker placed top memory first: TopScore={ranked[0].score:.4f} > SecondScore={ranked[1].score:.4f}")


def test_filtering_rules():
    section("3. MEMORY FILTERING RULES")

    filt = MemoryFilter(min_relevance=0.4, min_confidence=0.5, allow_private=False)
    now = time.time()

    from memory.models.query import MemoryResult

    # Valid candidate
    c1 = MemoryResult(
        memory=Memory(memory_id="c1", type=MemoryType.PREFERENCE, title="Valid", content="Valid content", metadata=MemoryMetadata(confidence=0.9, privacy_level="public")),
        score=0.7
    )
    # Expired candidate
    c2 = MemoryResult(
        memory=Memory(memory_id="c2", type=MemoryType.EPISODIC, title="Expired", content="Expired content", metadata=MemoryMetadata(expires_at=now - 100)),
        score=0.8
    )
    # Private candidate
    c3 = MemoryResult(
        memory=Memory(memory_id="c3", type=MemoryType.SEMANTIC, title="Private", content="Private key", metadata=MemoryMetadata(privacy_level="private")),
        score=0.9
    )
    # Low relevance candidate
    c4 = MemoryResult(
        memory=Memory(memory_id="c4", type=MemoryType.EPISODIC, title="Low Score", content="Irrelevant content", metadata=MemoryMetadata(confidence=0.9)),
        score=0.2
    )

    results = filt.filter([c1, c2, c3, c4], current_time=now)
    assert len(results) == 1
    assert results[0].memory.memory_id == "c1"
    print(f"[PASS] MemoryFilter retained only valid candidate (1/4 retained).")


def test_context_generator():
    section("4. CONTEXT GENERATION & WORD BUDGET")

    gen = MemoryContextGenerator(max_memories=3, max_word_budget=100)

    from memory.models.query import MemoryResult
    res1 = MemoryResult(
        memory=Memory(type=MemoryType.PREFERENCE, title="Dark Mode", content="User prefers dark theme across desktop apps.", metadata=MemoryMetadata(source="conversation")),
        score=0.92
    )
    res2 = MemoryResult(
        memory=Memory(type=MemoryType.SEMANTIC, title="Creator Fact", content="JARVIS was created by Chandrasekhar.", metadata=MemoryMetadata(source="chat")),
        score=0.85
    )

    pkg = gen.generate([res1, res2])
    assert pkg.has_context is True
    assert pkg.memory_count == 2
    assert "[Long-Term Memory Context]" in pkg.formatted_context
    assert "[PREFERENCE] Dark Mode" in pkg.formatted_context
    print(f"[PASS] Context Package generated: MemoryCount={pkg.memory_count} | WordCount={pkg.metadata['word_count']}")


async def test_retrieval_pipeline_e2e():
    section("5. END-TO-END RETRIEVAL PIPELINE & EVENT FLOW")

    mem_manager = MemoryManager(storage_provider=InMemoryStorageProvider())
    
    # Store memory
    m = Memory(
        memory_id="pref_vscode",
        type=MemoryType.PREFERENCE,
        title="VS Code Preferences",
        content="User prefers Python extension and Dark Plus theme in VS Code.",
        metadata=MemoryMetadata(importance_score=9.0, confidence=1.0)
    )
    await mem_manager.store_memory(m)

    pipeline = RetrievalPipeline(
        search_engine=CandidateSearchEngine(memory_storage=mem_manager._storage)
    )

    events_captured = []

    def log_event(event):
        events_captured.append(event.name)

    for evt in ["MemoryRetrieved", "CandidatesRanked", "CandidatesFiltered", "ContextGenerated"]:
        event_bus.subscribe(evt, log_event)

    query = MemoryQuery(query_text="python vscode preferences", top_k=5)
    pkg = await pipeline.execute(query)

    assert pkg.has_context is True
    assert pkg.memory_count == 1
    assert "VS Code Preferences" in pkg.formatted_context
    print(f"[PASS] End-to-end retrieval pipeline executed cleanly. Context formatted.")
    print(f"[PASS] EventBus emissions captured: {events_captured}")
    assert "MemoryRetrieved" in events_captured
    assert "CandidatesRanked" in events_captured
    assert "CandidatesFiltered" in events_captured
    assert "ContextGenerated" in events_captured

    cleanup_test_db()


async def main():
    await test_candidate_search()
    test_ranking_algorithm()
    test_filtering_rules()
    test_context_generator()
    await test_retrieval_pipeline_e2e()
    print("\n" + "=" * 60)
    print("  ALL MILESTONE 4.4 RETRIEVAL ENGINE TESTS PASSED SUCCESSFULLY!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
