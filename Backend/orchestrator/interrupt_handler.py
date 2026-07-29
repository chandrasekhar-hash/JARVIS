"""
Barge-In Interrupt Handler for J.A.R.V.I.S. Phase V1.6 Voice Orchestrator.
Halts assistant voice output playback immediately upon user speech detection during speaking state.
"""
import logging
from typing import Optional
from .interfaces import IInterruptHandler
from .models import SessionState, VoiceSession
from .state_machine import VoiceStateMachine
from .session_manager import SessionManager
from tts import voice_engine

logger = logging.getLogger("JARVIS_InterruptHandler")


class InterruptHandler(IInterruptHandler):
    """
    Handles user barge-in interruptions during assistant speech synthesis/playback.
    """

    def __init__(self, state_machine: VoiceStateMachine, session_manager: SessionManager):
        self.state_machine = state_machine
        self.session_manager = session_manager

    async def handle_barge_in(self, session_id: str) -> bool:
        session = self.session_manager.get_session(session_id)
        if not session:
            return False

        logger.info(f"[InterruptHandler] User barge-in detected for session '{session_id}'. Halting TTS playback.")

        # 1. Cancel TTS voice engine playback immediately
        try:
            await voice_engine.cancel()
        except Exception as e:
            logger.warning(f"[InterruptHandler] Error cancelling VoiceEngine: {e}")

        # 2. Increment statistics
        session.statistics.barge_in_count += 1

        # 3. Transition FSM state machine: SPEAKING -> INTERRUPTED -> LISTENING
        if self.state_machine.can_transition_to(SessionState.INTERRUPTED):
            self.state_machine.transition_to(SessionState.INTERRUPTED, reason="Barge-in interrupt")
            session.state = SessionState.INTERRUPTED

        if self.state_machine.can_transition_to(SessionState.LISTENING):
            self.state_machine.transition_to(SessionState.LISTENING, reason="Resume listening after barge-in")
            session.state = SessionState.LISTENING

        return True
