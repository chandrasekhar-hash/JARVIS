"""
Comprehensive Unit & Integration Test Suite for J.A.R.V.I.S. Phase P1.2 (Memory & Personalization).
Covers Memory CRUD, Categories (User Memory vs Knowledge), Expiration Policies, Dynamic Confidence Reinforcement,
Conflict Resolution / Versioning, Hybrid Search, Pinning, Merging & Splitting, Personalization Profiles,
Privacy Controls, Import/Export, Multi-User Isolation, EventBus integration, DIP compliance, and Schema v2 Migration.
"""
import os
import sys
import time
import inspect
import unittest
import asyncio

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from product.config import ProductConfig
from product.storage import SQLiteProductStorage
from product.memory.memory_models import (
    Memory,
    MemoryCategory,
    MemoryType,
    MemoryStatus,
    ImportanceLevel,
    RetentionPolicy,
    MemorySettings,
    PersonalizationProfile,
)
from product.memory.memory_store import SQLiteMemoryRepository
from product.memory.memory_search import MemorySearchEngine
from product.memory.memory_summarizer import MemorySummarizer
from product.memory.memory_context import MemoryContextBuilder
from product.memory.memory_settings import MemorySettingsManager
from product.memory.memory_engine import MemoryEngine
from product.memory.memory_interfaces import (
    IMemoryRepository,
    IPersonalizationRepository,
    IMemorySettingsRepository,
    IMemorySearchEngine,
    IMemorySummarizer,
    IMemoryContextBuilder,
)
from brain.event_bus import event_bus


class TestProductPhaseP12(unittest.TestCase):
    """
    Dedicated test suite for Phase P1.2 Memory & Personalization.
    """

    def setUp(self):
        """Set up in-memory storage and isolated MemoryEngine instances."""
        self.config = ProductConfig(db_path=":memory:")
        self.storage = SQLiteProductStorage(db_path=":memory:", config=self.config)
        self.repository = SQLiteMemoryRepository(product_storage_instance=self.storage)
        self.engine = MemoryEngine(repository=self.repository, bus=event_bus)

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """Clean up asyncio event loop."""
        self.loop.close()

    # -------------------------------------------------------------------------
    # 1. Memory CRUD & Retrieval Tests
    # -------------------------------------------------------------------------
    def test_01_memory_creation_and_retrieval(self):
        user_id = "usr_tony_01"
        mem = self.engine.create_memory(
            user_id=user_id,
            title="Favorite IDE",
            content="Tony Stark prefers Antigravity IDE and VS Code.",
            category=MemoryCategory.USER_MEMORY,
            memory_type=MemoryType.LONG_TERM,
            tags=["ide", "coding", "preferences"],
            importance_score=0.9,
            confidence_score=0.8,
        )

        self.assertIsNotNone(mem.memory_id)
        self.assertEqual(mem.user_id, user_id)
        self.assertEqual(mem.category, MemoryCategory.USER_MEMORY)
        self.assertIn("coding", mem.tags)

        # Retrieve memory
        fetched = self.engine.get_memory(user_id, mem.memory_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.title, "Favorite IDE")
        self.assertEqual(fetched.access_count, 2)  # Initial 1 + 1 get retrieval

    def test_02_memory_update_delete_archive_restore(self):
        user_id = "usr_bruce_01"
        mem = self.engine.create_memory(
            user_id=user_id,
            title="Lab Notes",
            content="Gamma radiation research notes.",
        )

        # Update
        updated = self.engine.update_memory(
            user_id=user_id,
            memory_id=mem.memory_id,
            title="Updated Gamma Notes",
            content="Updated research on gamma stabilization.",
            importance_score=0.95,
        )
        self.assertEqual(updated.title, "Updated Gamma Notes")
        self.assertEqual(updated.importance_score, 0.95)

        # Archive
        self.assertTrue(self.engine.archive_memory(user_id, mem.memory_id))
        archived = self.engine.get_memory(user_id, mem.memory_id)
        self.assertEqual(archived.status, MemoryStatus.ARCHIVED)

        # Restore
        self.assertTrue(self.engine.restore_memory(user_id, mem.memory_id))
        restored = self.engine.get_memory(user_id, mem.memory_id)
        self.assertEqual(restored.status, MemoryStatus.ACTIVE)

        # Delete
        self.assertTrue(self.engine.delete_memory(user_id, mem.memory_id))
        self.assertIsNone(self.engine.get_memory(user_id, mem.memory_id))

    # -------------------------------------------------------------------------
    # 2. Separation of Memory vs Knowledge
    # -------------------------------------------------------------------------
    def test_03_memory_categories_user_vs_knowledge(self):
        user_id = "usr_peter_01"

        # User Memory (personal fact)
        user_mem = self.engine.create_memory(
            user_id=user_id,
            title="Personal Fact",
            content="Peter Parker works at Daily Bugle as a photographer.",
            category=MemoryCategory.USER_MEMORY,
        )

        # Saved Knowledge (external doc)
        knowledge_mem = self.engine.create_memory(
            user_id=user_id,
            title="API Documentation",
            content="OAuth2 PKCE authorization flow implementation guide.",
            category=MemoryCategory.KNOWLEDGE,
        )

        user_memories = self.engine.list_memories(user_id, category=MemoryCategory.USER_MEMORY)
        knowledge_memories = self.engine.list_memories(user_id, category=MemoryCategory.KNOWLEDGE)

        self.assertEqual(len(user_memories), 1)
        self.assertEqual(user_memories[0].memory_id, user_mem.memory_id)

        self.assertEqual(len(knowledge_memories), 1)
        self.assertEqual(knowledge_memories[0].memory_id, knowledge_mem.memory_id)

    # -------------------------------------------------------------------------
    # 3. Retention & Expiration Lifecycle
    # -------------------------------------------------------------------------
    def test_04_memory_expiration_policies(self):
        user_id = "usr_steve_01"
        past_time = time.time() - 100.0  # Already expired

        # Expired Memory
        expired_mem = self.engine.create_memory(
            user_id=user_id,
            title="Temporary Context",
            content="Temporary meeting room code.",
            retention_policy=RetentionPolicy.SESSION_ONLY,
            expires_at=past_time,
        )

        # Permanent Memory
        permanent_mem = self.engine.create_memory(
            user_id=user_id,
            title="Shield Protocol",
            content="Permanent security clearance code.",
            retention_policy=RetentionPolicy.PERMANENT,
        )

        # Fetching memories should auto-evict expired records
        active = self.engine.list_memories(user_id)
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].memory_id, permanent_mem.memory_id)

    # -------------------------------------------------------------------------
    # 4. Dynamic Confidence Evolution
    # -------------------------------------------------------------------------
    def test_05_dynamic_confidence_reinforcement(self):
        user_id = "usr_rhodey_01"
        mem = self.engine.create_memory(
            user_id=user_id,
            title="Preferred Language",
            content="Rhodey prefers Python for backend scripting.",
            confidence_score=0.6,
        )

        # Reinforce twice
        self.engine.reinforce_confidence(user_id, mem.memory_id, boost=0.15)
        self.engine.reinforce_confidence(user_id, mem.memory_id, boost=0.15)

        updated = self.engine.get_memory(user_id, mem.memory_id)
        self.assertAlmostEqual(updated.confidence_score, 0.90, places=2)
        self.assertEqual(updated.reinforcement_count, 3)

    # -------------------------------------------------------------------------
    # 5. Conflict Resolution & Versioning
    # -------------------------------------------------------------------------
    def test_06_conflict_resolution_and_superseding(self):
        user_id = "usr_natasha_01"

        old_mem = self.engine.create_memory(
            user_id=user_id,
            title="Primary Language",
            content="Natasha uses C++ for system level exploits.",
        )

        new_mem = Memory(
            memory_id="mem_natasha_v2",
            user_id=user_id,
            title="Primary Language",
            content="Natasha uses Rust for system level exploits.",
        )

        old_res, new_res = self.repository.supersede_memory(user_id, old_mem.memory_id, new_mem)

        self.assertEqual(old_res.status, MemoryStatus.SUPERSEDED)
        self.assertEqual(old_res.superseded_by, new_res.memory_id)
        self.assertEqual(new_res.version, 2)
        self.assertEqual(new_res.content, "Natasha uses Rust for system level exploits.")

    # -------------------------------------------------------------------------
    # 6. Hybrid Search Engine Tests
    # -------------------------------------------------------------------------
    def test_07_hybrid_search_and_filtering(self):
        user_id = "usr_clint_01"

        m1 = self.engine.create_memory(
            user_id=user_id,
            title="Archery Gear",
            content="Composite bow with custom carbon fiber arrows.",
            tags=["archery", "gear"],
            importance_score=0.8,
        )
        m2 = self.engine.create_memory(
            user_id=user_id,
            title="Farm Location",
            content="Secluded farm house in Iowa.",
            tags=["location", "personal"],
            is_pinned=True,
        )

        # Keyword search
        res1 = self.engine.search_memory(user_id, query="bow carbon")
        self.assertEqual(res1.total_count, 1)
        self.assertEqual(res1.memories[0].memory_id, m1.memory_id)

        # Tag search
        res2 = self.engine.search_memory(user_id, query="", tags=["archery"])
        self.assertEqual(res2.total_count, 1)
        self.assertEqual(res2.memories[0].memory_id, m1.memory_id)

        # Pinned priority search
        res3 = self.engine.search_memory(user_id, query="farm bow")
        self.assertGreater(res3.total_count, 0)
        self.assertEqual(res3.memories[0].memory_id, m2.memory_id)  # Pinned item boosted first

    # -------------------------------------------------------------------------
    # 7. Pinning & Unpinning Tests
    # -------------------------------------------------------------------------
    def test_08_memory_pinning_and_unpinning(self):
        user_id = "usr_wanda_01"
        mem = self.engine.create_memory(
            user_id=user_id,
            title="Hex Spell",
            content="Reality manipulation spell notes.",
        )

        self.assertTrue(self.engine.pin_memory(user_id, mem.memory_id))
        pinned_mem = self.engine.get_memory(user_id, mem.memory_id)
        self.assertTrue(pinned_mem.is_pinned)

        self.assertTrue(self.engine.unpin_memory(user_id, mem.memory_id))
        unpinned_mem = self.engine.get_memory(user_id, mem.memory_id)
        self.assertFalse(unpinned_mem.is_pinned)

    # -------------------------------------------------------------------------
    # 8. Summarize, Merge, and Split Tests
    # -------------------------------------------------------------------------
    def test_09_memory_summarize_merge_and_split(self):
        user_id = "usr_vision_01"

        m1 = self.engine.create_memory(
            user_id=user_id,
            title="Mind Stone Part 1",
            content="The Mind Stone empowers artificial consciousness.",
        )
        m2 = self.engine.create_memory(
            user_id=user_id,
            title="Mind Stone Part 2",
            content="Vibranium density matrix stabilizes neural pathways.",
        )

        # Summarize
        summary_text = self.engine.summarize_memory([m1, m2])
        self.assertIn("Mind Stone Part 1", summary_text)

        # Merge
        merged = self.engine.merge_memories(user_id, [m1.memory_id, m2.memory_id], "Consolidated Mind Stone Spec")
        self.assertEqual(merged.title, "Consolidated Mind Stone Spec")
        self.assertIn("artificial consciousness", merged.content)
        self.assertIn("Vibranium density", merged.content)

        # Verify old memories were superseded
        self.assertEqual(self.engine.get_memory(user_id, m1.memory_id).status, MemoryStatus.SUPERSEDED)

        # Split
        split_items = self.engine.split_memory(user_id, merged.memory_id, split_delimiter="\n\n")
        self.assertEqual(len(split_items), 2)

    # -------------------------------------------------------------------------
    # 9. Personalization Profile Tests
    # -------------------------------------------------------------------------
    def test_10_personalization_profile_crud(self):
        user_id = "usr_fury_01"

        # Fetch default profile
        profile = self.engine.get_personalization(user_id)
        self.assertEqual(profile.preferred_assistant_name, "J.A.R.V.I.S.")

        # Update profile
        updated = self.engine.update_personalization(
            user_id=user_id,
            preferred_assistant_name="F.R.I.D.A.Y.",
            preferred_wake_word="FRIDAY",
            communication_style="direct_tactical",
            favorite_topics=["global_security", "avengers_initiative"],
        )

        self.assertEqual(updated.preferred_assistant_name, "F.R.I.D.A.Y.")
        self.assertEqual(updated.preferred_wake_word, "FRIDAY")
        self.assertEqual(updated.communication_style, "direct_tactical")
        self.assertIn("global_security", updated.favorite_topics)

    # -------------------------------------------------------------------------
    # 10. Privacy Controls & Export/Import Tests
    # -------------------------------------------------------------------------
    def test_11_privacy_controls_and_toggles(self):
        user_id = "usr_sam_01"
        self.engine.create_memory(user_id=user_id, title="Flight Spec", content="EXO-7 Falcon wingsuit specs.")

        # Disable memory
        self.engine.settings_manager.update_settings(user_id, memory_enabled=False)
        settings = self.engine.settings_manager.get_settings(user_id)
        self.assertFalse(settings.memory_enabled)

        # Clear memory
        cleared_count = self.engine.clear_memory(user_id)
        self.assertEqual(cleared_count, 1)
        self.assertEqual(len(self.engine.list_memories(user_id)), 0)

    def test_12_memory_export_and_import(self):
        user_id_src = "usr_export_src"
        user_id_dst = "usr_import_dst"

        self.engine.create_memory(user_id=user_id_src, title="Export Test", content="Sample memory for export.")
        self.engine.update_personalization(user_id=user_id_src, preferred_assistant_name="ExportAssistant")

        # Export
        exported_data = self.engine.export_memories(user_id_src)
        self.assertEqual(exported_data["user_id"], user_id_src)
        self.assertEqual(len(exported_data["memories"]), 1)

        # Import
        imported_count, msg = self.engine.import_memories(user_id_dst, exported_data)
        self.assertEqual(imported_count, 1)

        dst_memories = self.engine.list_memories(user_id_dst)
        self.assertEqual(len(dst_memories), 1)
        self.assertEqual(dst_memories[0].user_id, user_id_dst)  # Strictly user isolated

    # -------------------------------------------------------------------------
    # 11. Multi-User Isolation Tests
    # -------------------------------------------------------------------------
    def test_13_multi_user_isolation(self):
        user_a = "usr_alice"
        user_b = "usr_bob"

        m_a = self.engine.create_memory(user_id=user_a, title="Alice Strategy", content="Alice confidential alpha data.")
        m_b = self.engine.create_memory(user_id=user_b, title="Bob Payload", content="Bob confidential beta payload.")

        # User A cannot get User B memory
        self.assertIsNone(self.engine.get_memory(user_a, m_b.memory_id))

        # User A list memories should contain 1
        a_mems = self.engine.list_memories(user_a)
        self.assertEqual(len(a_mems), 1)
        self.assertEqual(a_mems[0].memory_id, m_a.memory_id)

        # User A search for User B specific terms should yield 0 results
        search_res = self.engine.search_memory(user_a, query="Bob Payload beta")
        self.assertEqual(search_res.total_count, 0)

    # -------------------------------------------------------------------------
    # 12. EventBus Integration Tests
    # -------------------------------------------------------------------------
    def test_14_eventbus_integration(self):
        events_received = []

        def listener(evt):
            events_received.append(evt.name)

        event_bus.subscribe("MemoryCreated", listener)
        event_bus.subscribe("MemoryUpdated", listener)
        event_bus.subscribe("MemoryPinned", listener)
        event_bus.subscribe("MemoryDeleted", listener)
        event_bus.subscribe("PersonalizationUpdated", listener)

        user_id = "usr_events_01"
        mem = self.engine.create_memory(user_id=user_id, title="Event Memory", content="Event bus testing.")
        self.engine.update_memory(user_id=user_id, memory_id=mem.memory_id, title="Event Memory V2")
        self.engine.pin_memory(user_id, mem.memory_id)
        self.engine.update_personalization(user_id, preferred_assistant_name="EventJARVIS")
        self.engine.delete_memory(user_id, mem.memory_id)

        self.assertIn("MemoryCreated", events_received)
        self.assertIn("MemoryUpdated", events_received)
        self.assertIn("MemoryPinned", events_received)
        self.assertIn("PersonalizationUpdated", events_received)
        self.assertIn("MemoryDeleted", events_received)

    # -------------------------------------------------------------------------
    # 13. Context Window Builder & Lifecycle Tests
    # -------------------------------------------------------------------------
    def test_15_context_window_builder(self):
        user_id = "usr_ctx_01"
        self.engine.create_memory(user_id=user_id, title="Pinned Fact", content="User prefers dark theme.", is_pinned=True)
        self.engine.create_memory(user_id=user_id, title="Working Context", content="Active code refactoring session.", memory_type=MemoryType.WORKING)

        ctx = self.engine.build_context_window(user_id, current_query="refactor code")
        self.assertEqual(ctx["user_id"], user_id)
        self.assertEqual(len(ctx["pinned_memories"]), 1)
        self.assertEqual(len(ctx["working_memory"]), 1)

    def test_16_schema_v2_migration(self):
        schema_ver = self.storage.get_schema_version()
        self.assertEqual(schema_ver, 2)

    def test_17_repository_dip_compliance(self):
        """
        Confirms domain services depend ONLY on abstract repository interfaces
        and contain ZERO direct imports of sqlite3 or SQLiteProductStorage.
        """
        domain_services = [
            MemorySearchEngine,
            MemorySummarizer,
            MemoryContextBuilder,
            MemorySettingsManager,
        ]

        for svc in domain_services:
            source = inspect.getsource(svc)
            self.assertNotIn("import sqlite3", source)
            self.assertNotIn("sqlite3.connect", source)
            self.assertNotIn("SQLiteProductStorage", source)

    def test_18_memory_engine_lifecycle_metrics_health(self):
        self.loop.run_until_complete(self.engine.start())
        self.assertTrue(self.engine._running)

        health = self.engine.get_health()
        metrics = self.engine.get_metrics()
        self.assertTrue(health["healthy"])
        self.assertEqual(metrics["phase"], "P1.2")

        self.loop.run_until_complete(self.engine.stop())
        self.assertFalse(self.engine._running)


if __name__ == "__main__":
    unittest.main()
