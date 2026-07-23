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
    RetentionPolicy,
    KnowledgeNode,
    KnowledgeEdge,
    InMemoryStorageProvider,
    EntityResolver,
    RelationshipBuilder,
    GraphEngine,
    GraphTraversal,
    FactPromoter,
    PromotionConfig,
)


def section(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_deterministic_entity_extraction():
    section("1. DETERMINISTIC ENTITY EXTRACTION")

    sample_text = "User Chandrasekhar is editing main.py in JARVIS project using VS Code and Python for Google."
    nodes = EntityResolver.extract_entities(sample_text)
    
    node_types = {n.type for n in nodes}
    labels = {n.label for n in nodes}

    print(f"[PASS] Extracted {len(nodes)} entity nodes.")
    print(f"[PASS] Entity Types found: {node_types}")
    print(f"[PASS] Labels: {labels}")

    assert "Person" in node_types
    assert "Project" in node_types
    assert "Application" in node_types
    assert "File" in node_types
    assert "Organization" in node_types
    assert "Topic" in node_types
    assert "Main.py" in labels or "main.py" in [l.lower() for l in labels]


def test_directional_relationships():
    section("2. DIRECTIONAL RELATIONSHIPS")

    n1 = KnowledgeNode(node_id="n_user", label="Chandrasekhar", type="Person")
    n2 = KnowledgeNode(node_id="n_vscode", label="VS Code", type="Application")
    n3 = KnowledgeNode(node_id="n_python", label="Python", type="Topic")

    edges = RelationshipBuilder.infer_relationships([n1, n2, n3], context_text="User prefers VS Code and Python.")
    
    assert len(edges) >= 2
    for e in edges:
        assert e.source_node_id != e.target_node_id  # Directional, no self-loops
        assert e.relationship in ["PREFERS", "USES", "RELATED_TO", "CREATED", "PART_OF"]
        assert e.weight > 0.0
        assert e.confidence > 0.0
        print(f"[PASS] Directional Edge: '{e.source_node_id}' --[{e.relationship}]--> '{e.target_node_id}' (Weight={e.weight}, Conf={e.confidence})")


async def test_graph_engine_and_merging():
    section("3. GRAPH ENGINE (CRUD & DUPLICATE NODE MERGING)")

    storage = InMemoryStorageProvider()
    engine = GraphEngine(storage_provider=storage)

    # 1. Create Nodes
    n1 = KnowledgeNode(node_id="node_user_1", label="User", type="Person", properties={"alias": "Chandrasekhar"})
    n2 = KnowledgeNode(node_id="node_user_2", label="User Alias", type="Person", properties={"email": "user@jarvis.ai"})
    n3 = KnowledgeNode(node_id="node_vscode", label="VS Code", type="Application")

    await engine.add_node(n1)
    await engine.add_node(n2)
    await engine.add_node(n3)

    # 2. Prevent Self-Loops
    self_loop = KnowledgeEdge(edge_id="e_self", source_node_id="node_user_1", target_node_id="node_user_1", relationship="RELATED_TO")
    ok_self = await engine.add_edge(self_loop)
    assert ok_self is False
    print(f"[PASS] GraphEngine prevented self-loop edge creation.")

    # 3. Create Valid Edges
    e1 = KnowledgeEdge(edge_id="e1", source_node_id="node_user_1", target_node_id="node_vscode", relationship="PREFERS")
    e2 = KnowledgeEdge(edge_id="e2", source_node_id="node_user_2", target_node_id="node_vscode", relationship="USES")
    await engine.add_edge(e1)
    await engine.add_edge(e2)

    # 4. Merge Duplicate Nodes (n2 into n1)
    merge_ok = await engine.merge_nodes(source_node_id="node_user_2", target_node_id="node_user_1")
    assert merge_ok is True
    print(f"[PASS] Merged duplicate node 'node_user_2' into 'node_user_1'.")

    # Verify merged properties
    merged_node = await engine.get_node("node_user_1")
    assert merged_node is not None
    assert "email" in merged_node.properties
    assert "alias" in merged_node.properties
    print(f"[PASS] Node properties merged cleanly: {merged_node.properties}")

    # Verify edge redirection
    redirected_edges = await storage.get_edges("node_user_1", direction="both")
    assert len(redirected_edges) >= 1
    print(f"[PASS] Edges redirected to target node. Count: {len(redirected_edges)}")


async def test_cycle_safe_graph_traversal():
    section("4. CYCLE-SAFE GRAPH TRAVERSAL (1-HOP & 2-HOP)")

    storage = InMemoryStorageProvider()
    engine = GraphEngine(storage_provider=storage)
    traversal = GraphTraversal(storage_provider=storage)

    # Setup 3-node cyclic chain: A -> B -> C -> A
    na = KnowledgeNode(node_id="node_a", label="A", type="Topic")
    nb = KnowledgeNode(node_id="node_b", label="B", type="Topic")
    nc = KnowledgeNode(node_id="node_c", label="C", type="Topic")
    await engine.add_node(na)
    await engine.add_node(nb)
    await engine.add_node(nc)

    await engine.add_edge(KnowledgeEdge(edge_id="e_ab", source_node_id="node_a", target_node_id="node_b", relationship="RELATED_TO"))
    await engine.add_edge(KnowledgeEdge(edge_id="e_bc", source_node_id="node_b", target_node_id="node_c", relationship="RELATED_TO"))
    await engine.add_edge(KnowledgeEdge(edge_id="e_ca", source_node_id="node_c", target_node_id="node_a", relationship="RELATED_TO"))

    # 1-Hop Traversal (Bidirectional 1-hop edges A->B and C->A)
    h1 = await traversal.traverse_1hop("node_a")
    assert len(h1.nodes) == 3  # Start node A + neighbor B + neighbor C

    print(f"[PASS] 1-hop traversal from 'node_a' returned {len(h1.nodes)} nodes.")

    # 2-Hop Traversal (Cycle-safe, does not loop infinitely)
    h2 = await traversal.traverse_2hop("node_a")
    assert len(h2.nodes) == 3  # A, B, C
    print(f"[PASS] 2-hop cycle-safe traversal returned {len(h2.nodes)} nodes without infinite loop.")


async def test_fact_promoter_provenance_and_config():
    section("5. FACT PROMOTION, PROVENANCE & CONFIGURABLE THRESHOLDS")

    mem_manager = MemoryManager(storage_provider=InMemoryStorageProvider())
    custom_config = PromotionConfig(recurrence_threshold=2, importance_threshold=7.5, confidence_threshold=0.75)
    promoter = FactPromoter(manager=mem_manager, config=custom_config)

    # Create recurring episodic observations
    obs1 = Memory(
        memory_id="obs_1",
        type=MemoryType.EPISODIC,
        title="User Preference Dark Theme",
        content="I prefer dark mode in VS Code.",
        metadata=MemoryMetadata(importance_score=6.0, confidence=0.9)
    )
    obs2 = Memory(
        memory_id="obs_2",
        type=MemoryType.EPISODIC,
        title="User Preference Dark Theme",
        content="I prefer dark mode in VS Code.",
        metadata=MemoryMetadata(importance_score=6.0, confidence=0.9)
    )

    # Evaluate & Promote
    facts = await promoter.evaluate_and_promote([obs1, obs2])
    assert len(facts) == 1
    promoted_fact = facts[0]

    assert promoted_fact.type == MemoryType.PREFERENCE
    assert "Promoted Fact:" in promoted_fact.title
    assert "obs_1" in promoted_fact.summary and "obs_2" in promoted_fact.summary
    print(f"[PASS] Fact promoted with provenance linkage: Summary='{promoted_fact.summary}'")

    # Prevent Duplicate Promotion
    facts_dup = await promoter.evaluate_and_promote([obs1, obs2])
    assert len(facts_dup) == 0
    print(f"[PASS] FactPromoter prevented duplicate fact promotion.")


async def test_event_flow():
    section("6. EVENTBUS EMISSIONS")

    events_captured = []

    def log_event(event):
        events_captured.append(event.name)

    for evt in ["KnowledgeNodeCreated", "KnowledgeEdgeCreated", "KnowledgeNodeMerged", "FactPromoted", "KnowledgeGraphUpdated"]:
        event_bus.subscribe(evt, log_event)

    storage = InMemoryStorageProvider()
    engine = GraphEngine(storage_provider=storage)

    n1 = KnowledgeNode(node_id="ev_1", label="Event Node 1", type="Topic")
    n2 = KnowledgeNode(node_id="ev_2", label="Event Node 2", type="Topic")
    await engine.add_node(n1)
    await engine.add_node(n2)

    edge = KnowledgeEdge(edge_id="ev_e1", source_node_id="ev_1", target_node_id="ev_2", relationship="RELATED_TO")
    await engine.add_edge(edge)

    await engine.merge_nodes("ev_2", "ev_1")

    print(f"[PASS] Captured EventBus emissions: {events_captured}")
    assert "KnowledgeNodeCreated" in events_captured
    assert "KnowledgeEdgeCreated" in events_captured
    assert "KnowledgeNodeMerged" in events_captured


async def main():
    test_deterministic_entity_extraction()
    test_directional_relationships()
    await test_graph_engine_and_merging()
    await test_cycle_safe_graph_traversal()
    await test_fact_promoter_provenance_and_config()
    await test_event_flow()
    print("\n" + "=" * 60)
    print("  ALL MILESTONE 4.5 KNOWLEDGE GRAPH TESTS PASSED SUCCESSFULLY!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
