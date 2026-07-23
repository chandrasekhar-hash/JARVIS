import sys
import os
import asyncio

# Ensure Backend directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from typing import Optional, List
from brain.event_bus import event_bus

from memory import (
    memory_manager,
    MemoryManager,
    Memory,
    MemoryType,
    RetentionPolicy,
    MemoryMetadata,
    MemoryChunk,
    KnowledgeNode,
    KnowledgeEdge,
    MemoryQuery,
    MemoryResult,
    MemorySummary,
    BaseMemoryStorageProvider,
    InMemoryStorageProvider,
)


def section(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_schema_validation():
    section("1. SCHEMA & METADATA VALIDATION")
    
    # Create Memory with default metadata
    mem = Memory(
        type=MemoryType.PREFERENCE,
        title="User Preferred Editor",
        content="The user's preferred code editor is Visual Studio Code."
    )
    
    assert mem.memory_id is not None
    assert mem.type == MemoryType.PREFERENCE
    assert mem.metadata.importance_score == 5.0
    assert mem.metadata.confidence == 1.0
    assert mem.metadata.retention_policy == RetentionPolicy.EPISODIC
    print(f"[PASS] Memory model instantiated: ID={mem.memory_id[:8]}... | Type={mem.type.value}")
    
    # KnowledgeNode validation
    node = KnowledgeNode(label="VS Code", type="Application", properties={"path": "code.exe"})
    assert node.label == "VS Code"
    assert node.type == "Application"
    print(f"[PASS] KnowledgeNode model validated: NodeID={node.node_id[:8]}... | Label='{node.label}'")
    
    # KnowledgeEdge validation
    edge = KnowledgeEdge(source_node_id=node.node_id, target_node_id="user_1", relationship="PREFERS")
    assert edge.relationship == "PREFERS"
    print(f"[PASS] KnowledgeEdge model validated: Relationship='{edge.relationship}'")


async def test_memory_manager_crud():
    section("2. MEMORY MANAGER CRUD OPERATIONS")
    
    captured_events = []
    def on_event(event):
        captured_events.append(event.name)

    event_bus.subscribe("MemoryCreated", on_event)
    event_bus.subscribe("MemoryUpdated", on_event)
    event_bus.subscribe("MemoryArchived", on_event)
    event_bus.subscribe("MemoryForgotten", on_event)

    # 1. Store Memory
    m1 = Memory(
        type=MemoryType.SEMANTIC,
        title="JARVIS Creator Fact",
        content="JARVIS was created by Chandrasekhar.",
        metadata=MemoryMetadata(importance_score=9.0, retention_policy=RetentionPolicy.PERMANENT, tags=["creator", "system"])
    )
    mem_id = await memory_manager.store_memory(m1)
    assert mem_id == m1.memory_id
    print(f"[PASS] store_memory succeeded: ID={mem_id[:8]}...")
    
    # 2. Get Memory
    retrieved = await memory_manager.get_memory(mem_id)
    assert retrieved is not None
    assert retrieved.title == "JARVIS Creator Fact"
    assert retrieved.metadata.access_count == 1
    print(f"[PASS] get_memory succeeded: AccessCount={retrieved.metadata.access_count}")

    # 3. Update Memory
    updated = await memory_manager.update_memory(mem_id, {"title": "JARVIS System Creator", "importance_score": 10.0})
    assert updated is not None
    assert updated.title == "JARVIS System Creator"
    assert updated.metadata.importance_score == 10.0
    print(f"[PASS] update_memory succeeded: Title='{updated.title}' | Importance={updated.metadata.importance_score}")

    # 4. List Memories
    listed = await memory_manager.list_memories(memory_type="semantic")
    assert len(listed) >= 1
    print(f"[PASS] list_memories succeeded: Count={len(listed)}")

    # 5. Archive Memory
    arch_ok = await memory_manager.archive_memory(mem_id)
    assert arch_ok is True
    ret_arch = await memory_manager.get_memory(mem_id)
    assert "archived" in ret_arch.metadata.tags
    print(f"[PASS] archive_memory succeeded: Tags={ret_arch.metadata.tags}")

    # 6. Store Second Memory for Selective Forgetting
    m2 = Memory(
        type=MemoryType.EPISODIC,
        title="Temporary Note",
        content="Opened notepad briefly.",
        metadata=MemoryMetadata(tags=["temp", "scratch"])
    )
    m2_id = await memory_manager.store_memory(m2)

    # 7. Forget Memory (Selective Forgetting)
    purged_count = await memory_manager.forget_memory(tag="temp")
    assert purged_count == 1
    assert await memory_manager.get_memory(m2_id) is None
    print(f"[PASS] forget_memory (selective) succeeded: PurgedCount={purged_count}")

    # 8. Delete Memory (Hard Delete)
    del_ok = await memory_manager.delete_memory(mem_id)
    assert del_ok is True
    assert await memory_manager.get_memory(mem_id) is None
    print(f"[PASS] delete_memory succeeded for ID={mem_id[:8]}...")

    # Verify EventBus Emissions
    print(f"[PASS] EventBus emissions captured: {captured_events}")
    assert "MemoryCreated" in captured_events
    assert "MemoryUpdated" in captured_events
    assert "MemoryArchived" in captured_events
    assert "MemoryForgotten" in captured_events


async def test_provider_independence():
    section("3. PROVIDER INDEPENDENCE & SUMMARY TELEMETRY")
    
    # Test custom mock provider swapping
    class DummyCustomProvider(BaseMemoryStorageProvider):
        def __init__(self):
            self.store = {}
        async def store_memory(self, memory: Memory) -> str:
            self.store[memory.memory_id] = memory
            return memory.memory_id
        async def get_memory(self, memory_id: str) -> Optional[Memory]:
            return self.store.get(memory_id)
        async def update_memory(self, memory_id: str, updates: dict) -> Optional[Memory]:
            return None
        async def delete_memory(self, memory_id: str) -> bool:
            return bool(self.store.pop(memory_id, None))
        async def archive_memory(self, memory_id: str) -> bool:
            return True
        async def list_memories(self, memory_type=None, tag=None, limit=50, offset=0) -> list:
            return list(self.store.values())
        async def get_summary(self) -> MemorySummary:
            return MemorySummary(total_memories=len(self.store))

    custom_provider = DummyCustomProvider()
    test_mgr = MemoryManager(storage_provider=custom_provider)
    
    dummy_mem = Memory(type=MemoryType.PROJECT, title="Custom Provider Test", content="Testing provider independence.")
    stored_id = await test_mgr.store_memory(dummy_mem)
    fetched = await test_mgr.get_memory(stored_id)
    assert fetched is not None
    assert fetched.title == "Custom Provider Test"
    print(f"[PASS] Swapped custom storage provider executed cleanly.")

    # Telemetry Summary Check
    summary = await memory_manager.get_summary()
    assert isinstance(summary, MemorySummary)
    print(f"[PASS] MemorySummary telemetry: TotalMemories={summary.total_memories} | Bytes={summary.storage_bytes}")


async def main():
    test_schema_validation()
    await test_memory_manager_crud()
    await test_provider_independence()
    print("\n" + "=" * 60)
    print("  ALL MILESTONE 4.1 MEMORY CORE TESTS PASSED SUCCESSFULLY!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
