import sys
import os
import time
import asyncio
from typing import List

# Ensure Backend directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app
from brain.event_bus import event_bus
from brain.context import desktop_context, DesktopContextManager
from memory import (
    MemoryManager,
    Memory,
    MemoryType,
    MemoryMetadata,
    ObservationCapture,
    ingestion_pipeline,
    retrieval_pipeline,
    fact_promoter,
    memory_context_provider,
    InMemoryStorageProvider,
    EntityResolver,
    RelationshipBuilder,
    graph_engine,
)


def section(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


async def test_full_phase4_e2e_scenario():
    section("1. END-TO-END MEMORY PIPELINE (INGESTION -> PROMOTION -> RETRIEVAL -> CONTEXT)")

    # Use isolated test storage manager
    test_manager = MemoryManager(storage_provider=InMemoryStorageProvider())
    ingestion_pipeline.manager = test_manager
    retrieval_pipeline.search_engine.memory_storage = test_manager._storage
    fact_promoter.manager = test_manager
    memory_context_provider.pipeline.search_engine.memory_storage = test_manager._storage

    events_captured = []

    def log_event(event):
        events_captured.append(event.name)

    for evt in [
        "ObservationCaptured", "ObservationValidated", "ObservationClassified",
        "MemoryCreated", "FactPromoted", "MemoryRetrieved", "CandidatesRanked",
        "CandidatesFiltered", "ContextGenerated", "KnowledgeNodeCreated", "KnowledgeEdgeCreated"
    ]:
        event_bus.subscribe(evt, log_event)


    # 1. Capture & Ingest Observation 1
    obs1 = ObservationCapture.from_conversation("I prefer Dark Mode and Python in VS Code", "Preference recorded.")
    obs1_id = await ingestion_pipeline.process_observation(obs1)
    assert obs1_id is not None
    print(f"[PASS] IngestionPipeline processed observation 1: ID='{obs1_id[:8]}...'")

    # Capture & Ingest Observation 2 (Recurring)
    obs2 = ObservationCapture.from_conversation("I prefer Dark Mode and Python in VS Code", "Preference recorded.")
    obs2_id = await ingestion_pipeline.process_observation(obs2)

    # 2. Fact Promotion
    obs_mem1 = await ingestion_pipeline.manager.get_memory(obs1_id)
    obs_mem2 = await ingestion_pipeline.manager.get_memory(obs2_id)
    candidates = [m for m in [obs_mem1, obs_mem2] if m is not None]

    promoted = await fact_promoter.evaluate_and_promote(candidates)
    print(f"[PASS] FactPromoter evaluated observations. Promoted count: {len(promoted)}")

    # 3. Knowledge Graph Entity Resolution & Relationship Construction
    nodes = EntityResolver.extract_entities(obs1.content)
    edges = RelationshipBuilder.infer_relationships(nodes, context_text=obs1.content)
    for n in nodes:
        await graph_engine.add_node(n)
    for e in edges:
        await graph_engine.add_edge(e)
    print(f"[PASS] Knowledge Graph created {len(nodes)} nodes and {len(edges)} edges.")

    # 4. Memory Retrieval & Context Package Generation
    ctx_pkg = await memory_context_provider.pipeline.execute(
        MemoryQuery(query_text="What are the user preferences for VS Code?")
    )
    assert ctx_pkg.has_context is True
    assert ctx_pkg.memory_count >= 1
    print(f"[PASS] RetrievalPipeline generated Context Package with {ctx_pkg.memory_count} memories.")

    # 5. DesktopContextManager Merged Brain Context
    intent = "Open VS Code with my preferred theme and language"
    merged_context = desktop_context.get_context_summary(intent)
    assert merged_context is not None
    assert "Dark Mode" in merged_context or "VS Code" in merged_context
    print(f"[PASS] DesktopContextManager merged Memory context into Brain context.")
    print(f"[PASS] EventBus emissions captured: {set(events_captured)}")


def test_phase4_rest_apis():
    section("2. PHASE 4 MEMORY REST API ENDPOINTS")

    from memory import memory_manager, ingestion_pipeline
    ingestion_pipeline.manager = memory_manager

    client = TestClient(app)


    # 1. POST /api/memory/store
    res_store = client.post("/api/memory/store", json={
        "title": "User Preferred Language",
        "content": "User prefers English and Python.",
        "type": "preference",
        "tags": ["user", "language"]
    })
    assert res_store.status_code == 200
    data_store = res_store.json()
    assert data_store["status"] == "success"
    mem_id = data_store["memory_id"]
    print(f"[PASS] POST /api/memory/store response: MemoryID='{mem_id}'")

    # 2. POST /api/memory/query
    res_query = client.post("/api/memory/query", json={
        "query_text": "What is user preferred language?",
        "top_k": 3
    })
    assert res_query.status_code == 200
    data_query = res_query.json()
    assert data_query["status"] == "success"
    assert data_query["has_context"] is True
    print(f"[PASS] POST /api/memory/query response: MemoryCount={data_query['memory_count']}")

    # 3. GET /api/memory/summary
    res_sum = client.get("/api/memory/summary")
    assert res_sum.status_code == 200
    data_sum = res_sum.json()
    assert data_sum["status"] == "success"
    print(f"[PASS] GET /api/memory/summary response: TotalMemories={data_sum['total_memories']}")

    # 4. GET /api/memory/graph
    res_graph = client.get("/api/memory/graph")
    assert res_graph.status_code == 200
    data_graph = res_graph.json()
    assert data_graph["status"] == "success"
    print(f"[PASS] GET /api/memory/graph response: Nodes={data_graph['total_nodes']} | Edges={data_graph['total_edges']}")

    # 5. POST /api/memory/forget
    res_forget = client.post("/api/memory/forget", json={"memory_id": mem_id})
    assert res_forget.status_code == 200
    data_forget = res_forget.json()
    assert data_forget["status"] == "success"
    print(f"[PASS] POST /api/memory/forget response: Status='{data_forget['status']}'")


async def main():
    await test_full_phase4_e2e_scenario()
    test_phase4_rest_apis()
    print("\n" + "=" * 60)
    print("  ALL PHASE 4 END-TO-END INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    from memory.models.query import MemoryQuery
    asyncio.run(main())
