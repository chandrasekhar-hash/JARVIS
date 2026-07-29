"""
Comprehensive Unit & Integration Test Suite for J.A.R.V.I.S. Phase V1.3 Conversation Engine.
"""
import unittest
import asyncio
import time
from typing import List

from conversation.models import (
    ConversationSession,
    ConversationState,
    ConversationTurn,
    TurnState,
    IntentType,
)
from conversation.engine import ConversationContinuityEngine
from conversation.response_provider import MockResponseProvider, ResponseProviderFactory
from conversation.state_machine import ConversationStateMachine, ConversationStateEnum
from conversation.intent_processor import IntentProcessor
from conversation.metrics import ConversationMetrics
from speech.events import SpeechFinalEvent, SpeechPartialEvent
from brain.event_bus import EventBus


class TestConversationEngineV13(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.bus = EventBus()

    def tearDown(self):
        self.loop.close()

    def test_01_single_turn_processing(self):
        async def run_test():
            engine = ConversationContinuityEngine(
                response_provider=MockResponseProvider(),
                bus=self.bus,
            )
            session = engine.start_session("test_user_1")
            res = await engine.process_turn(session.session_id, "What is the status of the system?")

            self.assertTrue(res.success)
            self.assertIsNotNone(res.current_turn)
            self.assertEqual(res.current_turn.state, TurnState.COMPLETED)
            self.assertIn("Answer to query", res.assistant_response)

        self.loop.run_until_complete(run_test())

    def test_02_multi_turn_history_and_trimming(self):
        async def run_test():
            engine = ConversationContinuityEngine(
                response_provider=MockResponseProvider(),
                bus=self.bus,
                max_history_turns=5,
            )
            session = engine.start_session("test_user_2")

            for i in range(8):
                await engine.process_turn(session.session_id, f"Query turn number {i + 1}")

            history = engine.get_history(session.session_id)
            self.assertEqual(len(history), 5)
            self.assertEqual(history[-1].user_text, "Query turn number 8")

        self.loop.run_until_complete(run_test())

    def test_03_speech_final_event_integration_exactly_one_turn(self):
        async def run_test():
            emitted_events: List[str] = []

            def listener(evt):
                emitted_events.append(evt.name)

            self.bus.subscribe("ConversationTurnCompleted", listener)

            engine = ConversationContinuityEngine(
                response_provider=MockResponseProvider(),
                bus=self.bus,
            )

            # Emit SpeechFinalEvent
            speech_evt = SpeechFinalEvent(
                session_id="spc_test_123",
                transcript="What is system status?",
                confidence=0.95,
                language="english",
                duration_sec=1.5,
            )

            engine.event_bus.emit("speech_final", **speech_evt.__dict__)

            # Allow async task to complete
            await asyncio.sleep(0.1)

            self.assertEqual(emitted_events.count("ConversationTurnCompleted"), 1)

            # Re-emitting identical SpeechFinalEvent transcript should be ignored (deduplicated)
            engine.event_bus.emit("speech_final", **speech_evt.__dict__)
            await asyncio.sleep(0.1)
            self.assertEqual(emitted_events.count("ConversationTurnCompleted"), 1)

        self.loop.run_until_complete(run_test())

    def test_04_ignore_speech_partial_events(self):
        async def run_test():
            emitted_events: List[str] = []

            def listener(evt):
                emitted_events.append(evt.name)

            self.bus.subscribe("ConversationTurnStarted", listener)

            engine = ConversationContinuityEngine(
                response_provider=MockResponseProvider(),
                bus=self.bus,
            )

            partial_evt = SpeechPartialEvent(
                session_id="spc_test_partial",
                transcript="What is",
                confidence=0.9,
                language="english",
            )

            engine.event_bus.emit("speech_partial", **partial_evt.__dict__)
            await asyncio.sleep(0.05)

            self.assertEqual(len(emitted_events), 0)

        self.loop.run_until_complete(run_test())

    def test_05_follow_up_reference_resolution(self):
        async def run_test():
            engine = ConversationContinuityEngine(
                response_provider=MockResponseProvider(),
                bus=self.bus,
            )
            session = engine.start_session("test_user_3")

            await engine.process_turn(session.session_id, "Check main.py file")
            res2 = await engine.process_turn(session.session_id, "What about that?")

            self.assertTrue(res2.success)
            self.assertGreater(len(res2.resolved_references), 0)
            self.assertEqual(res2.resolved_references[0].expression, "that")
            self.assertEqual(res2.resolved_references[0].resolved_target, "main.py")

        self.loop.run_until_complete(run_test())

    def test_06_state_machine_transitions(self):
        sm = ConversationStateMachine()
        self.assertEqual(sm.current_state, ConversationStateEnum.IDLE)
        self.assertTrue(sm.transition_to(ConversationStateEnum.LISTENING))
        self.assertTrue(sm.transition_to(ConversationStateEnum.THINKING))
        self.assertTrue(sm.transition_to(ConversationStateEnum.RESPONDING))
        self.assertTrue(sm.transition_to(ConversationStateEnum.WAITING))
        self.assertTrue(sm.transition_to(ConversationStateEnum.IDLE))

    def test_07_turn_cancellation(self):
        async def run_test():
            engine = ConversationContinuityEngine(
                response_provider=MockResponseProvider(),
                bus=self.bus,
            )
            session = engine.start_session("test_user_4")
            await engine.process_turn(session.session_id, "Heavy processing turn")

            ok = engine.cancel_turn(session.session_id)
            self.assertTrue(ok)
            history = engine.get_history(session.session_id)
            self.assertEqual(history[-1].state, TurnState.CANCELLED)

        self.loop.run_until_complete(run_test())

    def test_08_intent_processor(self):
        ip = IntentProcessor()

        res_q = ip.classify_intent("How does this engine work?")
        self.assertEqual(res_q.intent, IntentType.QUESTION)

        res_cmd = ip.classify_intent("Run security audit")
        self.assertEqual(res_cmd.intent, IntentType.COMMAND)

        res_follow = ip.classify_intent("What about that?", has_resolved_references=True)
        self.assertEqual(res_follow.intent, IntentType.FOLLOW_UP)

    def test_09_session_management_apis(self):
        engine = ConversationContinuityEngine(bus=self.bus)
        session = engine.start_session("test_user_5")

        state = engine.get_state(session.session_id)
        self.assertEqual(state.session_id, session.session_id)

        ok_clear = engine.clear_history(session.session_id)
        self.assertTrue(ok_clear)

        ok_end = engine.end_session(session.session_id)
        self.assertTrue(ok_end)

    def test_10_empty_transcript_handling(self):
        async def run_test():
            engine = ConversationContinuityEngine(bus=self.bus)
            res = await engine.process_turn("sess_empty", "   ")
            self.assertFalse(res.success)
            self.assertIn("Empty or whitespace", res.error_message)

        self.loop.run_until_complete(run_test())


if __name__ == "__main__":
    unittest.main()
