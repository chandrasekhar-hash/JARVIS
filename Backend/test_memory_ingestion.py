import sys
import os
import time
import asyncio
from typing import List

# Ensure Backend directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from brain.event_bus import event_bus
from memory import memory_manager, MemoryType
from memory.ingestion import (
    RawObservation,
    ObservationCapture,
    ObservationValidator,
    ObservationClassifier,
    ObservationDeduplicator,
    IngestionPipeline,
)


def section(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_capture_normalization():
    section("1. OBSERVATION CAPTURE NORMALIZATION")
    
    # 1. Conversation
    obs1 = ObservationCapture.from_conversation("Open VS Code", "Opening Visual Studio Code...")
    assert obs1.source == "conversation"
    assert "User: Open VS Code" in obs1.content
    print(f"[PASS] Conversation capture normalized: Source='{obs1.source}' | Title='{obs1.title}'")

    # 2. Vision
    vis_data = {
        "active_app": {"app_name": "Visual Studio Code", "window_title": "main.py - JARVIS", "category": "coding"},
        "headline": "User active in Visual Studio Code",
        "full_text": "import asyncio\nfrom memory import memory_manager"
    }
    obs2 = ObservationCapture.from_vision(vis_data)
    assert obs2.source == "vision"
    assert "Headline: User active in Visual Studio Code" in obs2.content
    print(f"[PASS] Vision capture normalized: Source='{obs2.source}' | Category='coding'")

    # 3. Tool Execution
    obs3 = ObservationCapture.from_tool_execution("browser_open_url", {"urls": ["https://google.com"]}, "Success")
    assert obs3.source == "tool_execution"
    assert "Executed Tool 'browser_open_url'" in obs3.content
    print(f"[PASS] Tool execution capture normalized: Source='{obs3.source}'")

    # 4. File Context
    obs4 = ObservationCapture.from_file("d:/JARVIS/Backend/main.py", "FastAPI entry point for backend server.")
    assert obs4.source == "file"
    assert "File Path: d:/JARVIS/Backend/main.py" in obs4.content
    print(f"[PASS] File context capture normalized: Source='{obs4.source}'")


def test_validation_rules():
    section("2. OBSERVATION VALIDATION RULES")

    # Valid Observation
    valid_obs = RawObservation(source="conversation", content="This is a valid observation text.")
    res = ObservationValidator.validate(valid_obs)
    assert res.is_valid is True
    print(f"[PASS] Valid observation passed validation.")

    # Short Content Rejection
    short_obs = RawObservation(source="conversation", content="hi")
    res_short = ObservationValidator.validate(short_obs)
    assert res_short.is_valid is False
    assert "too short" in res_short.reason
    print(f"[PASS] Short content rejected: Reason='{res_short.reason}'")

    # Unsupported Source Rejection
    bad_src = RawObservation(source="telepathy", content="Testing invalid source.")
    res_src = ObservationValidator.validate(bad_src)
    assert res_src.is_valid is False
    assert "Unsupported observation source" in res_src.reason
    print(f"[PASS] Unsupported source rejected: Reason='{res_src.reason}'")

    # Timestamp Skew Rejection
    future_obs = RawObservation(source="conversation", content="Future message", timestamp=time.time() + 500.0)
    res_fut = ObservationValidator.validate(future_obs)
    assert res_fut.is_valid is False
    assert "future" in res_fut.reason
    print(f"[PASS] Timestamp future skew rejected: Reason='{res_fut.reason}'")


def test_classification_accuracy():
    section("3. RULE-BASED CLASSIFICATION ACCURACY")

    classifier = ObservationClassifier()

    # Preference Memory
    pref_obs = RawObservation(source="conversation", content="I prefer dark mode and natural Indian English tone.")
    mtype, meta = classifier.classify(pref_obs)
    assert mtype == MemoryType.PREFERENCE
    assert meta.importance_score == 8.5
    print(f"[PASS] Classified Preference Memory: Type='{mtype.value}' | Importance={meta.importance_score}")

    # Project Memory
    proj_obs = RawObservation(source="file", content="Editing the workspace repository architecture spec.")
    mtype2, meta2 = classifier.classify(proj_obs)
    assert mtype2 == MemoryType.PROJECT
    print(f"[PASS] Classified Project Memory: Type='{mtype2.value}'")

    # Procedural Memory
    proc_obs = RawObservation(source="tool_execution", content="Executed tool app_open with args {'name': 'notepad'}")
    mtype3, meta3 = classifier.classify(proc_obs)
    assert mtype3 == MemoryType.PROCEDURAL
    print(f"[PASS] Classified Procedural Memory: Type='{mtype3.value}'")

    # Semantic Memory
    sem_obs = RawObservation(source="conversation", content="JARVIS is defined as an intelligent AI assistant.")
    mtype4, meta4 = classifier.classify(sem_obs)
    assert mtype4 == MemoryType.SEMANTIC
    print(f"[PASS] Classified Semantic Memory: Type='{mtype4.value}'")

    # Episodic Memory (Default)
    ep_obs = RawObservation(source="conversation", content="What is the weather today?")
    mtype5, meta5 = classifier.classify(ep_obs)
    assert mtype5 == MemoryType.EPISODIC
    print(f"[PASS] Classified Episodic Memory: Type='{mtype5.value}'")


async def test_deduplication_engine():
    section("4. DEDUPLICATION ENGINE")

    dedup = ObservationDeduplicator(similarity_threshold=0.90)

    # Store initial memory into memory_manager
    initial_obs = RawObservation(source="conversation", content="Remember that Chandrasekhar is my creator.")
    mtype, meta = ObservationClassifier.classify(initial_obs)
    from memory import Memory, MemoryChunk
    mem = Memory(
        memory_id=initial_obs.observation_id,
        type=mtype,
        title=initial_obs.title,
        content=initial_obs.content,
        chunks=[MemoryChunk(memory_id=initial_obs.observation_id, content=initial_obs.content)],
        metadata=meta
    )
    await memory_manager.store_memory(mem)

    existing_memories = await memory_manager.list_memories(limit=100)

    # 1. Exact Duplicate
    exact_obs = RawObservation(source="conversation", content="Remember that Chandrasekhar is my creator.")
    is_dup1, match1 = dedup.is_duplicate(exact_obs, existing_memories)
    assert is_dup1 is True
    assert match1 == initial_obs.observation_id
    print(f"[PASS] Exact duplicate detected: MatchedID={match1[:8]}...")

    # 2. Near Duplicate (Similarity > 0.90)
    near_obs = RawObservation(source="conversation", content="Remember that Chandrasekhar is my creator!")
    is_dup2, match2 = dedup.is_duplicate(near_obs, existing_memories)
    assert is_dup2 is True
    print(f"[PASS] Near duplicate detected: MatchedID={match2[:8]}...")

    # 3. Unique Observation
    unique_obs = RawObservation(source="conversation", content="The user's favorite programming language is Python.")
    is_dup3, match3 = dedup.is_duplicate(unique_obs, existing_memories)
    assert is_dup3 is False
    assert match3 is None
    print(f"[PASS] Unique observation passed duplicate check.")

    # Cleanup
    await memory_manager.delete_memory(initial_obs.observation_id)


async def test_pipeline_execution():
    section("5. END-TO-END INGESTION PIPELINE & EVENT FLOW")

    pipeline = IngestionPipeline(manager=memory_manager)
    events_captured = []

    def log_event(event):
        events_captured.append(event.name)

    for evt in ["ObservationCaptured", "ObservationValidated", "ObservationRejected", "ObservationClassified", "ObservationDeduplicated"]:
        event_bus.subscribe(evt, log_event)

    # Ingest valid unique preference observation
    obs = ObservationCapture.from_conversation("I prefer dark mode in all applications.", "Got it. Preference noted.")
    mem_id = await pipeline.process_observation(obs)
    assert mem_id is not None
    print(f"[PASS] Pipeline stored unique memory: ID={mem_id[:8]}...")

    # Verify stored memory properties
    stored_mem = await memory_manager.get_memory(mem_id)
    assert stored_mem is not None
    assert stored_mem.type == MemoryType.PREFERENCE
    assert "dark mode" in stored_mem.content
    print(f"[PASS] Memory verified in MemoryManager: Type='{stored_mem.type.value}' | Importance={stored_mem.metadata.importance_score}")

    # Ingest duplicate observation - should be prevented
    dup_obs = ObservationCapture.from_conversation("I prefer dark mode in all applications.", "Got it. Preference noted.")
    dup_id = await pipeline.process_observation(dup_obs)
    assert dup_id is None

    print(f"[PASS] Pipeline prevented storage of duplicate observation.")

    # Verify event emissions
    print(f"[PASS] Captured EventBus emissions: {events_captured}")
    assert "ObservationCaptured" in events_captured
    assert "ObservationValidated" in events_captured
    assert "ObservationClassified" in events_captured
    assert "ObservationDeduplicated" in events_captured

    # Cleanup
    await memory_manager.delete_memory(mem_id)


async def main():
    test_capture_normalization()
    test_validation_rules()
    test_classification_accuracy()
    await test_deduplication_engine()
    await test_pipeline_execution()
    print("\n" + "=" * 60)
    print("  ALL MILESTONE 4.2 INGESTION PIPELINE TESTS PASSED SUCCESSFULLY!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
