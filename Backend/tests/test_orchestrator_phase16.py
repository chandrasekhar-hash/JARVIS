"""
Comprehensive Unit & Integration Test Suite for J.A.R.V.I.S. Phase V1.6 Voice Orchestrator.
"""
import unittest
import asyncio
from typing import List

from orchestrator.config import OrchestratorConfig
from orchestrator.models import SessionState, VoiceSession, ConversationTurn, OrchestratorResult
from orchestrator.state_machine import VoiceStateMachine, InvalidStateTransitionError
from orchestrator.session_manager import SessionManager
from orchestrator.history import ConversationHistory
from orchestrator.health import HealthMonitor
from orchestrator.recovery import RecoveryPolicyManager
from orchestrator.commands import (
    StartSessionCommand,
    CancelSessionCommand,
    PauseConversationCommand,
    ResumeConversationCommand,
    StopSpeakingCommand,
    ResetSessionCommand,
)
from orchestrator.coordinator import OrchestratorCoordinator
from orchestrator.metrics import orchestrator_metrics
from orchestrator.engine import VoiceOrchestrator
from brain.event_bus import EventBus


class TestVoiceOrchestratorV16(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.bus = EventBus()
        orchestrator_metrics.reset()

    def tearDown(self):
        self.loop.close()

    def test_01_state_machine_valid_and_invalid_transitions(self):
        sm = VoiceStateMachine()
        self.assertEqual(sm.current_state, SessionState.IDLE)

        # Valid transition: IDLE -> LISTENING
        self.assertTrue(sm.transition_to(SessionState.LISTENING))

        # Valid transition: LISTENING -> PROCESSING_AUDIO
        self.assertTrue(sm.transition_to(SessionState.PROCESSING_AUDIO))

        # Invalid transition: PROCESSING_AUDIO -> SPEAKING (Must go through TRANSCRIBING -> THINKING -> PREPARING_RESPONSE)
        with self.assertRaises(InvalidStateTransitionError):
            sm.transition_to(SessionState.SPEAKING)

    def test_02_session_manager_crud(self):
        sm = SessionManager()
        session = sm.create_session(user_id="usr_test")

        self.assertIsNotNone(session.session_id)
        self.assertEqual(sm.get_session(session.session_id).user_id, "usr_test")

        sm.pause_session(session.session_id)
        self.assertEqual(session.state, SessionState.PAUSED)

        sm.resume_session(session.session_id)
        self.assertEqual(session.state, SessionState.LISTENING)

        sm.cancel_session(session.session_id)
        self.assertEqual(session.state, SessionState.CANCELLED)

    def test_03_explicit_commands_execution(self):
        async def run_test():
            coord = OrchestratorCoordinator(bus=self.bus)

            # StartSessionCommand
            res_start = await coord.execute_command(StartSessionCommand(user_id="usr_cmd"))
            self.assertTrue(res_start.success)
            sess_id = res_start.session_id

            # PauseConversationCommand
            res_pause = await coord.execute_command(PauseConversationCommand(session_id=sess_id))
            self.assertTrue(res_pause.success)

            # ResumeConversationCommand
            res_resume = await coord.execute_command(ResumeConversationCommand(session_id=sess_id))
            self.assertTrue(res_resume.success)

            # CancelSessionCommand
            res_cancel = await coord.execute_command(CancelSessionCommand(session_id=sess_id, reason="test"))
            self.assertTrue(res_cancel.success)

        self.loop.run_until_complete(run_test())

    def test_04_barge_in_interrupt_handler(self):
        async def run_test():
            coord = OrchestratorCoordinator(bus=self.bus)
            res_start = await coord.execute_command(StartSessionCommand(user_id="usr_barge"))
            sess_id = res_start.session_id

            session = coord.session_manager.get_session(sess_id)
            session.state = SessionState.SPEAKING
            coord.state_machine._current_state = SessionState.SPEAKING

            # Execute StopSpeakingCommand (Barge-In)
            res_barge = await coord.execute_command(StopSpeakingCommand(session_id=sess_id, reason="user_spoke"))
            self.assertTrue(res_barge.success)
            self.assertEqual(session.statistics.barge_in_count, 1)

        self.loop.run_until_complete(run_test())

    def test_05_health_monitor_subsystem_tracking(self):
        hm = HealthMonitor()
        self.assertTrue(hm.is_healthy())

        hm.record_error("Speech", "STT service timeout")
        self.assertFalse(hm.is_healthy())

        status = hm.get_status()
        self.assertFalse(status["overall_healthy"])
        self.assertIn("Speech", status["subsystems"])
        self.assertFalse(status["subsystems"]["Speech"]["healthy"])

    def test_06_recovery_policy_evaluation(self):
        rpm = RecoveryPolicyManager()
        res_retry = rpm.evaluate("speech_recognition_failure", {"retry_count": 1})
        self.assertEqual(res_retry, "retry")

        res_abort = rpm.evaluate("timeout")
        self.assertEqual(res_abort, "abort")

    def test_07_conversation_history_pruning(self):
        ch = ConversationHistory(max_history_turns=2)
        ch.add_turn("s1", ConversationTurn(turn_id="t1", session_id="s1", user_text="Q1"))
        ch.add_turn("s1", ConversationTurn(turn_id="t2", session_id="s1", user_text="Q2"))
        ch.add_turn("s1", ConversationTurn(turn_id="t3", session_id="s1", user_text="Q3"))

        history = ch.get_history("s1")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].turn_id, "t2")
        self.assertEqual(history[1].turn_id, "t3")

    def test_08_voice_orchestrator_public_api(self):
        async def run_test():
            orch = VoiceOrchestrator(bus=self.bus)
            await orch.start()

            res = await orch.start_session(user_id="usr_api")
            self.assertTrue(res.success)
            sess_id = res.session_id

            session = orch.get_session(sess_id)
            self.assertIsNotNone(session)

            res_cancel = await orch.cancel_session(sess_id)
            self.assertTrue(res_cancel.success)

            metrics = orch.get_metrics()
            self.assertEqual(metrics["total_sessions"], 1)

            health = orch.get_health()
            self.assertTrue(health["overall_healthy"])

            await orch.stop()

        self.loop.run_until_complete(run_test())


if __name__ == "__main__":
    unittest.main()
