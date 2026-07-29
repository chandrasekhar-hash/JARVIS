"""
Session Lifecycle Manager for J.A.R.V.I.S. Phase V1.6 Voice Orchestrator.
Manages session launching, completion teardown, reset, recovery, and restart routines.
"""
import time
import logging
from typing import Optional

from .interfaces import ILifecycleManager
from .models import VoiceSession, SessionState
from .session_manager import SessionManager
from .state_machine import VoiceStateMachine
from .recovery import RecoveryPolicyManager

logger = logging.getLogger("JARVIS_LifecycleManager")


class LifecycleManager(ILifecycleManager):
    """
    Coordinates voice session lifecycle transitions and clean teardown.
    """

    def __init__(
        self,
        session_manager: SessionManager,
        state_machine: VoiceStateMachine,
        recovery_manager: Optional[RecoveryPolicyManager] = None,
    ):
        self.session_manager = session_manager
        self.state_machine = state_machine
        self.recovery_manager = recovery_manager or RecoveryPolicyManager()

    async def start_session(self, user_id: str = "default_user") -> VoiceSession:
        """Launches a new voice session and transitions state machine to LISTENING."""
        session = self.session_manager.create_session(user_id=user_id)
        if self.state_machine.can_transition_to(SessionState.LISTENING):
            self.state_machine.transition_to(SessionState.LISTENING, reason="Session started")
        session.state = self.state_machine.current_state
        return session

    async def finish_session(self, session_id: str) -> bool:
        """Finishes target session cleanly."""
        session = self.session_manager.get_session(session_id)
        if not session:
            return False

        if self.state_machine.can_transition_to(SessionState.COMPLETED):
            self.state_machine.transition_to(SessionState.COMPLETED, reason="Session finished cleanly")

        session.state = SessionState.COMPLETED
        session.statistics.total_duration_sec = round(time.time() - session.started_at, 2)
        return True

    async def reset(self) -> None:
        """Resets orchestrator lifecycle state to IDLE."""
        if self.state_machine.can_transition_to(SessionState.IDLE):
            self.state_machine.transition_to(SessionState.IDLE, reason="Orchestrator reset")

    async def recover(self, session_id: str, failure_type: str) -> bool:
        """Applies explicit recovery policy for a failure condition."""
        policy_action = self.recovery_manager.evaluate(failure_type)
        session = self.session_manager.get_session(session_id)

        if session:
            session.statistics.recovery_count += 1

        if policy_action == "retry":
            if self.state_machine.can_transition_to(SessionState.LISTENING):
                self.state_machine.transition_to(SessionState.LISTENING, reason="Recovery retry")
            return True
        elif policy_action == "restart":
            await self.reset()
            return True
        else:  # abort
            if self.state_machine.can_transition_to(SessionState.ERROR):
                self.state_machine.transition_to(SessionState.ERROR, reason="Recovery abort")
            return False
