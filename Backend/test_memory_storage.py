import sys
import os
import asyncio
from typing import Optional, List

# Ensure Backend directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from memory import (
    MemoryManager,
    Memory,
    MemoryType,
    RetentionPolicy,
    MemoryMetadata,
    MemoryChunk,
    KnowledgeNode,
    KnowledgeEdge,
    MemorySummary,
    SQLiteMemoryStorageProvider,
    SQLiteVectorStorageProvider,
    SQLiteGraphStorageProvider,
    StorageProviderFactory,
    InMemoryStorageProvider,
)

TEST_DB_PATH = "logs/test_jarvis_memory.db"


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


async def test_sqlite_memory_provider():
    section("1. SQLITE MEMORY STORAGE PROVIDER (PERSISTENCE & CRUD)")
    cleanup_test_db()
    
    provider = SQLiteMemoryStorageProvider(db_path=TEST_DB_PATH)

    # 1. Store Memory
    mem1 = Memory(
        type=MemoryType.PREFERENCE,
        title="User Preferred Theme",
        content="The user's preferred theme is Dark Mode.",
        metadata=MemoryMetadata(importance_score=8.0, tags=["ui", "theme"])
    )
    mem_id1 = await provider.store_memory(mem1)
    assert mem_id1 == mem1.memory_id
    print(f"[PASS] SQLite store_memory succeeded: ID={mem_id1[:8]}...")

    # 2. Get Memory & Check Access Count
    fetched = await provider.get_memory(mem_id1)
    assert fetched is not None
    assert fetched.title == "User Preferred Theme"
    assert fetched.metadata.access_count == 1
    print(f"[PASS] SQLite get_memory succeeded: AccessCount={fetched.metadata.access_count}")

    # 3. Update Memory
    updated = await provider.update_memory(mem_id1, {"title": "User Preferred System Theme", "importance_score": 9.5})
    assert updated is not None
    assert updated.title == "User Preferred System Theme"
    assert updated.metadata.importance_score == 9.5
    print(f"[PASS] SQLite update_memory succeeded: Title='{updated.title}' | Importance={updated.metadata.importance_score}")

    # 4. List Memories with Filter
    memories = await provider.list_memories(memory_type="preference", tag="theme")
    assert len(memories) == 1
    print(f"[PASS] SQLite list_memories filtered count: {len(memories)}")

    # 5. Archive Memory
    arch_ok = await provider.archive_memory(mem_id1)
    assert arch_ok is True
    re_arch = await provider.get_memory(mem_id1)
    assert "archived" in re_arch.metadata.tags
    print(f"[PASS] SQLite archive_memory succeeded: Tags={re_arch.metadata.tags}")

    # 6. Summary Telemetry
    summary = await provider.get_summary()
    assert summary.total_memories == 1
    assert summary.count_by_type.get("preference") == 1
    print(f"[PASS] SQLite summary telemetry: Total={summary.total_memories} | Bytes={summary.storage_bytes}")


async def test_sqlite_vector_provider():
    section("2. VECTOR STORAGE PROVIDER & COSINE SIMILARITY SEARCH")
    
    vec_provider = SQLiteVectorStorageProvider(db_path=TEST_DB_PATH)

    # 1. Add Vector Embeddings
    chunk1 = MemoryChunk(memory_id="mem_1", content="Python artificial intelligence assistant", embedding=[1.0, 0.0, 0.0])
    chunk2 = MemoryChunk(memory_id="mem_2", content="Visual Studio Code text editor", embedding=[0.0, 1.0, 0.0])
    chunk3 = MemoryChunk(memory_id="mem_3", content="Machine learning python scripts", embedding=[0.8, 0.2, 0.0])

    await vec_provider.add_vector(chunk1)
    await vec_provider.add_vector(chunk2)
    await vec_provider.add_vector(chunk3)
    print(f"[PASS] Added 3 vector chunk embeddings to SQLite index.")

    # 2. Get Vector
    v = await vec_provider.get_vector(chunk1.chunk_id)
    assert v == [1.0, 0.0, 0.0]
    print(f"[PASS] get_vector retrieved vector embedding: {v}")

    # 3. Vector Similarity Search
    query_vec = [0.9, 0.1, 0.0]  # Close to chunk1 & chunk3
    results = await vec_provider.search_vectors(query_vec, top_k=2)
    assert len(results) == 2
    top_match = results[0]
    assert top_match["chunk_id"] == chunk1.chunk_id
    assert top_match["score"] > 0.90
    print(f"[PASS] Cosine vector search top match: ChunkID={top_match['chunk_id'][:8]}... | Score={top_match['score']}")


async def test_sqlite_graph_provider():
    section("3. GRAPH STORAGE PROVIDER (NODE & EDGE PERSISTENCE)")

    graph_provider = SQLiteGraphStorageProvider(db_path=TEST_DB_PATH)

    # 1. Add Nodes
    n1 = KnowledgeNode(label="User", type="Person", properties={"name": "Chandrasekhar"})
    n2 = KnowledgeNode(label="VS Code", type="Application", properties={"exe": "code.exe"})

    await graph_provider.add_node(n1)
    await graph_provider.add_node(n2)
    print(f"[PASS] Added Knowledge Nodes: n1='{n1.label}', n2='{n2.label}'")

    # 2. Add Edge
    edge = KnowledgeEdge(source_node_id=n1.node_id, target_node_id=n2.node_id, relationship="PREFERS", weight=1.0)
    await graph_provider.add_edge(edge)
    print(f"[PASS] Added Knowledge Edge: {n1.label} --[{edge.relationship}]--> {n2.label}")

    # 3. Query Outbound Edges
    edges = await graph_provider.get_edges(n1.node_id, direction="outbound")
    assert len(edges) == 1
    assert edges[0].relationship == "PREFERS"
    print(f"[PASS] get_edges query found relationship: '{edges[0].relationship}'")


async def test_persistence_across_restarts():
    section("4. PERSISTENCE ACROSS PROCESS RESTARTS")

    # Simulate restart by instantiating new SQLiteMemoryStorageProvider on existing database file
    new_provider_instance = SQLiteMemoryStorageProvider(db_path=TEST_DB_PATH)
    memories = await new_provider_instance.list_memories()
    assert len(memories) >= 1
    reloaded_mem = memories[0]
    assert "User Preferred System Theme" in reloaded_mem.title
    print(f"[PASS] Verified persistence across restart: Loaded memory '{reloaded_mem.title}' from SQLite DB file.")


async def test_provider_factory_and_manager():
    section("5. PROVIDER FACTORY & MEMORY MANAGER INTEGRATION")

    # Test SQLite Provider via Factory
    sql_prov = StorageProviderFactory.get_memory_provider(provider_type="sqlite", db_path=TEST_DB_PATH)
    assert isinstance(sql_prov, SQLiteMemoryStorageProvider)
    print(f"[PASS] StorageProviderFactory returned SQLiteMemoryStorageProvider.")

    # Test InMemory Provider via Factory
    mem_prov = StorageProviderFactory.get_memory_provider(provider_type="in_memory")
    assert isinstance(mem_prov, InMemoryStorageProvider)
    print(f"[PASS] StorageProviderFactory returned InMemoryStorageProvider.")

    # Test MemoryManager with Factory Provider
    mgr = MemoryManager(storage_provider=sql_prov)
    mem = Memory(type=MemoryType.PROJECT, title="Factory Managed Project", content="Testing MemoryManager factory integration.")
    stored_id = await mgr.store_memory(mem)
    assert await mgr.get_memory(stored_id) is not None
    print(f"[PASS] MemoryManager stored and fetched memory using Factory provider.")

    cleanup_test_db()


async def main():
    await test_sqlite_memory_provider()
    await test_sqlite_vector_provider()
    await test_sqlite_graph_provider()
    await test_persistence_across_restarts()
    await test_provider_factory_and_manager()
    print("\n" + "=" * 60)
    print("  ALL MILESTONE 4.3 STORAGE PROVIDER TESTS PASSED SUCCESSFULLY!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
