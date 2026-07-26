import os
import sys
import time
import asyncio
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from conversation.models import (
    ConversationSession,
    ConversationState,
    Topic,
    ConversationSummary,
    ContinuityValidation,
    ConversationResult,
)
from conversation.session_manager import SessionManager
from conversation.topic_manager import TopicManager
from conversation.context_tracker import ContextTracker
from conversation.continuity_validator import ContinuityValidator
from conversation.engine import ConversationContinuityEngine
from brain.event_bus import EventBus


class TestConversationPhase7(unittest.IsolatedAsyncioTestCase):

    async def test_session_creation_and_restoration_sla(self):
        manager = SessionManager()

        session = manager.create_session("u_conv_1")
        self.assertTrue(session.is_active)
        self.assertEqual(session.user_id, "u_conv_1")

        # Session Restore SLA < 30 ms
        start = time.perf_counter()
        restored = manager.restore_session(session.session_id)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        self.assertLess(elapsed_ms, 30.0)
        self.assertIsNotNone(restored)
        self.assertEqual(restored.session_id, session.session_id)

    async def test_topic_tracking_and_switching_sla(self):
        topic_mgr = TopicManager()
        state = ConversationState(session_id="s_topic_1")

        start = time.perf_counter()
        trans1 = topic_mgr.track_topic("Let's write python code for the build pipeline", state)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        # Topic tracking SLA < 20 ms
        self.assertLess(elapsed_ms, 20.0)
        self.assertIsNotNone(trans1)
        self.assertEqual(state.active_topic.topic_name, "software_engineering")

        # Topic switch
        trans2 = topic_mgr.track_topic("Open chrome browser and search for docs", state)
        self.assertIsNotNone(trans2)
        self.assertEqual(trans2.from_topic, "software_engineering")
        self.assertEqual(trans2.to_topic, "web_browsing")

    async def test_reference_resolution_sla(self):
        tracker = ContextTracker()
        state = ConversationState(
            session_id="s_ref_1",
            last_target_object="main.py",
            last_turn_text="Please check main.py",
        )

        # Resolve pronoun "that" / "it"
        start = time.perf_counter()
        resolved = tracker.resolve_references("Can you edit that?", state)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        # SLA < 20 ms
        self.assertLess(elapsed_ms, 20.0)
        self.assertGreater(len(resolved), 0)
        self.assertEqual(resolved[0].expression, "that")
        self.assertEqual(resolved[0].resolved_target, "main.py")

    async def test_context_tracker_state_update(self):
        tracker = ContextTracker()
        state = ConversationState(session_id="s_upd_1")

        updated_state = tracker.update_context(state, "Modifying engine.py for performance")
        self.assertEqual(updated_state.turn_count, 1)
        self.assertEqual(updated_state.last_target_object, "engine.py")

    async def test_continuity_validator(self):
        validator = ContinuityValidator()
        state = ConversationState(session_id="s_val_1")
        summary = ConversationSummary(
            short_summary="Turn 1: hello",
            working_summary="Working context",
            long_term_summary="Long term context",
        )

        validation = validator.validate_continuity(state, summary)
        self.assertTrue(validation.is_consistent)
        self.assertGreaterEqual(validation.coherence_score, 0.70)

    async def test_conversation_engine_full_pipeline_and_sla(self):
        engine = ConversationContinuityEngine()

        start = time.perf_counter()
        result = await engine.process_turn("s_pipeline_1", "Edit main.py file and run that again")
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        # Full pipeline SLA < 100 ms
        self.assertLess(elapsed_ms, 100.0)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.session)
        self.assertIsNotNone(result.summary)
        self.assertIsNotNone(result.validation)
        self.assertGreater(len(result.resolved_references), 0)

    async def test_event_publishing(self):
        custom_bus = EventBus()
        events_emitted = []

        def listener(evt):
            events_emitted.append(evt.name)

        custom_bus.subscribe("ConversationStarted", listener)
        custom_bus.subscribe("ConversationUpdated", listener)
        custom_bus.subscribe("TopicChanged", listener)
        custom_bus.subscribe("ReferenceResolved", listener)
        custom_bus.subscribe("ConversationSummarised", listener)

        sess_mgr = SessionManager(bus=custom_bus)
        engine = ConversationContinuityEngine(session_manager=sess_mgr, bus=custom_bus)

        session = sess_mgr.create_session("u_event")
        await engine.process_turn(session.session_id, "Explain python code in main.py file and edit that")
        await asyncio.sleep(0.05)

        self.assertIn("ConversationStarted", events_emitted)
        self.assertIn("ConversationUpdated", events_emitted)
        self.assertIn("TopicChanged", events_emitted)
        self.assertIn("ReferenceResolved", events_emitted)
        self.assertIn("ConversationSummarised", events_emitted)


if __name__ == "__main__":
    unittest.main()
