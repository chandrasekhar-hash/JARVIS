"""
Global Coordinator Engine for J.A.R.V.I.S. Phase V1.6 Voice Orchestrator.
Coordinates commands, events, FSM state machine transitions, timeout watchdogs, barge-in,
and health metrics across subsystems.
"""
import uuid
import time
import inspect
import asyncio
import logging
from typing import Optional, Dict, Any, Union

from .config import OrchestratorConfig, orchestrator_config
from .models import (
    SessionState,
    VoiceSession,
    ConversationTurn,
    OrchestratorResult,
)
from .state_machine import VoiceStateMachine, InvalidStateTransitionError
from .session_manager import SessionManager
from .history import ConversationHistory
from .health import HealthMonitor
from .recovery import RecoveryPolicyManager
from .lifecycle import LifecycleManager
from .interrupt_handler import InterruptHandler
from .timeout_manager import TimeoutManager
from .metrics import orchestrator_metrics, OrchestratorMetrics
from .commands import (
    StartSessionCommand,
    CancelSessionCommand,
    PauseConversationCommand,
    ResumeConversationCommand,
    StopSpeakingCommand,
    ResetSessionCommand,
)
from .events import (
    SessionStarted,
    SessionCompleted,
    SessionInterrupted,
    SessionRecovered,
    SessionCancelled,
    StateChanged,
    OrchestratorError,
)
from brain.event_bus import event_bus, EventBus

logger = logging.getLogger("JARVIS_OrchestratorCoordinator")


class OrchestratorCoordinator:
    """
    Central decision-making coordinator directing execution across subsystem managers.
    """

    def __init__(
        self,
        config: Optional[OrchestratorConfig] = None,
        session_manager: Optional[SessionManager] = None,
        state_machine: Optional[VoiceStateMachine] = None,
        history_manager: Optional[ConversationHistory] = None,
        health_monitor: Optional[HealthMonitor] = None,
        bus: Optional[EventBus] = None,
    ):
        self.config = config or orchestrator_config
        self.event_bus = bus or event_bus
        self.metrics = orchestrator_metrics

        self.state_machine = state_machine or VoiceStateMachine()
        self.session_manager = session_manager or SessionManager(max_sessions=self.config.max_sessions)
        self.history_manager = history_manager or ConversationHistory(max_history_turns=self.config.max_conversation_turns)
        self.health_monitor = health_monitor or HealthMonitor()
        self.recovery_manager = RecoveryPolicyManager()
        self.timeout_manager = TimeoutManager()

        self.lifecycle_manager = LifecycleManager(
            session_manager=self.session_manager,
            state_machine=self.state_machine,
            recovery_manager=self.recovery_manager,
        )
        self.interrupt_handler = InterruptHandler(
            state_machine=self.state_machine,
            session_manager=self.session_manager,
        )

        from .router import EventRouter
        self.router = EventRouter(coordinator_handler=self.handle_event, bus=self.event_bus)

    # ----------------------------------------------------
    # Command Execution Handlers
    # ----------------------------------------------------
    async def execute_command(
        self,
        cmd: Union[
            StartSessionCommand,
            CancelSessionCommand,
            PauseConversationCommand,
            ResumeConversationCommand,
            StopSpeakingCommand,
            ResetSessionCommand,
        ],
    ) -> OrchestratorResult:
        """Executes explicit intent command."""

        if isinstance(cmd, StartSessionCommand):
            return await self._handle_start_session_cmd(cmd)

        elif isinstance(cmd, CancelSessionCommand):
            return await self._handle_cancel_session_cmd(cmd)

        elif isinstance(cmd, PauseConversationCommand):
            return await self._handle_pause_conversation_cmd(cmd)

        elif isinstance(cmd, ResumeConversationCommand):
            return await self._handle_resume_conversation_cmd(cmd)

        elif isinstance(cmd, StopSpeakingCommand):
            return await self._handle_stop_speaking_cmd(cmd)

        elif isinstance(cmd, ResetSessionCommand):
            return await self._handle_reset_session_cmd(cmd)

        return OrchestratorResult(success=False, error="Unknown command")

    async def _handle_start_session_cmd(self, cmd: StartSessionCommand) -> OrchestratorResult:
        session = await self.lifecycle_manager.start_session(user_id=cmd.user_id)
        if cmd.conversation_id:
            session.conversation_id = cmd.conversation_id
        session.correlation_id = cmd.correlation_id
        self.metrics.total_sessions += 1

        # Emit StateChanged & SessionStarted
        state_evt = StateChanged(
            session_id=session.session_id,
            conversation_id=session.conversation_id,
            correlation_id=session.correlation_id,
            from_state=SessionState.IDLE.value,
            to_state=SessionState.LISTENING.value,
        )
        self.event_bus.emit("StateChanged", **state_evt.__dict__)

        start_evt = SessionStarted(
            session_id=session.session_id,
            conversation_id=session.conversation_id,
            correlation_id=session.correlation_id,
            user_id=session.user_id,
        )
        self.event_bus.emit("SessionStarted", **start_evt.__dict__)

        # Schedule conversation timeout watchdog
        self.timeout_manager.start_timeout(
            session.session_id,
            "conversation",
            self.config.conversation_timeout_seconds,
            self._handle_timeout,
        )

        return OrchestratorResult(success=True, session_id=session.session_id, state=session.state)

    async def _handle_cancel_session_cmd(self, cmd: CancelSessionCommand) -> OrchestratorResult:
        session = self.session_manager.get_session(cmd.session_id)
        if not session:
            return OrchestratorResult(success=False, error=f"Session '{cmd.session_id}' not found")

        if self.state_machine.can_transition_to(SessionState.CANCELLING):
            self.state_machine.transition_to(SessionState.CANCELLING, reason=cmd.reason)

        if self.state_machine.can_transition_to(SessionState.CANCELLED):
            self.state_machine.transition_to(SessionState.CANCELLED, reason=cmd.reason)

        self.session_manager.cancel_session(cmd.session_id, reason=cmd.reason)
        self.metrics.total_cancellations += 1
        self.timeout_manager.cancel_all_for_session(cmd.session_id)

        cancel_evt = SessionCancelled(
            session_id=session.session_id,
            conversation_id=session.conversation_id,
            correlation_id=session.correlation_id,
            reason=cmd.reason,
        )
        self.event_bus.emit("SessionCancelled", **cancel_evt.__dict__)

        if self.state_machine.can_transition_to(SessionState.COMPLETED):
            self.state_machine.transition_to(SessionState.COMPLETED, reason="Cancelled session teardown")
            session.state = SessionState.COMPLETED

        return OrchestratorResult(success=True, session_id=session.session_id, state=session.state)

    async def _handle_pause_conversation_cmd(self, cmd: PauseConversationCommand) -> OrchestratorResult:
        session = self.session_manager.get_session(cmd.session_id)
        if not session:
            return OrchestratorResult(success=False, error=f"Session '{cmd.session_id}' not found")

        if self.state_machine.can_transition_to(SessionState.PAUSED):
            self.state_machine.transition_to(SessionState.PAUSED, reason="User pause command")
            self.session_manager.pause_session(cmd.session_id)
            return OrchestratorResult(success=True, session_id=session.session_id, state=SessionState.PAUSED)

        return OrchestratorResult(success=False, session_id=session.session_id, error="Cannot pause from current state")

    async def _handle_resume_conversation_cmd(self, cmd: ResumeConversationCommand) -> OrchestratorResult:
        session = self.session_manager.get_session(cmd.session_id)
        if not session:
            return OrchestratorResult(success=False, error=f"Session '{cmd.session_id}' not found")

        if self.state_machine.can_transition_to(SessionState.LISTENING):
            self.state_machine.transition_to(SessionState.LISTENING, reason="User resume command")
            self.session_manager.resume_session(cmd.session_id)
            return OrchestratorResult(success=True, session_id=session.session_id, state=SessionState.LISTENING)

        return OrchestratorResult(success=False, session_id=session.session_id, error="Cannot resume from current state")

    async def _handle_stop_speaking_cmd(self, cmd: StopSpeakingCommand) -> OrchestratorResult:
        session = self.session_manager.get_session(cmd.session_id)
        if not session:
            return OrchestratorResult(success=False, error=f"Session '{cmd.session_id}' not found")

        if session.state == SessionState.SPEAKING:
            ok = await self.interrupt_handler.handle_barge_in(cmd.session_id)
            self.metrics.total_barge_ins += 1
            interrupt_evt = SessionInterrupted(
                session_id=session.session_id,
                conversation_id=session.conversation_id,
                correlation_id=session.correlation_id,
                reason=cmd.reason,
            )
            self.event_bus.emit("SessionInterrupted", **interrupt_evt.__dict__)
            return OrchestratorResult(success=ok, session_id=session.session_id, state=session.state)

        return OrchestratorResult(success=True, session_id=session.session_id, state=session.state)

    async def _handle_reset_session_cmd(self, cmd: ResetSessionCommand) -> OrchestratorResult:
        await self.lifecycle_manager.reset()
        return OrchestratorResult(success=True, state=SessionState.IDLE)

    # ----------------------------------------------------
    # Event Routing & Canonical Flow Execution
    # ----------------------------------------------------
    def handle_event(self, event_name: str, data: Dict[str, Any]) -> None:
        """Subsystem EventBus listener callback dispatching canonical flow handling."""
        self.health_monitor.record_activity("EventBus")

        if event_name == "WakeWordDetected":
            self.health_monitor.record_activity("WakeWord")
            if inspect.iscoroutinefunction(self._on_wake_word_detected):
                asyncio.create_task(self._on_wake_word_detected(data))
            else:
                asyncio.run(self._on_wake_word_detected(data))

        elif event_name in ("AudioInputReceived", "EnhancedAudioReady"):
            self.health_monitor.record_activity("Audio")
            if self.state_machine.can_transition_to(SessionState.PROCESSING_AUDIO):
                self.state_machine.transition_to(SessionState.PROCESSING_AUDIO, reason="Audio frames processing")

        elif event_name == "TranscriptReady" or event_name == "speech_final":
            self.health_monitor.record_activity("Speech")
            transcript = data.get("transcript", "").strip() if isinstance(data, dict) else ""
            if transcript:
                if self.state_machine.can_transition_to(SessionState.THINKING):
                    self.state_machine.transition_to(SessionState.THINKING, reason="Transcript ready for LLM thinking")

        elif event_name == "ConversationResponseReady":
            self.health_monitor.record_activity("Conversation")
            if self.state_machine.can_transition_to(SessionState.PREPARING_RESPONSE):
                self.state_machine.transition_to(SessionState.PREPARING_RESPONSE, reason="Response ready for TTS")

        elif event_name == "SpeechPlaybackStarted":
            self.health_monitor.record_activity("Voice")
            if self.state_machine.can_transition_to(SessionState.SPEAKING):
                self.state_machine.transition_to(SessionState.SPEAKING, reason="Assistant voice output speaking")

        elif event_name == "SpeechPlaybackCompleted":
            self.health_monitor.record_activity("Voice")
            if self.state_machine.can_transition_to(SessionState.WAITING_FOR_USER):
                self.state_machine.transition_to(SessionState.WAITING_FOR_USER, reason="Playback completed")

        elif event_name in ("SpeechPlaybackCancelled", "SpeechPlaybackError"):
            self.health_monitor.record_error("Voice", data.get("message", "Playback error"))

    async def _on_wake_word_detected(self, data: Dict[str, Any]) -> None:
        """Handles WakeWordDetected event."""
        active_sess = self.session_manager.get_active_session()

        # If assistant is currently speaking, treat wake word as barge-in interrupt
        if active_sess and active_sess.state == SessionState.SPEAKING and self.config.enable_barge_in:
            await self.execute_command(StopSpeakingCommand(session_id=active_sess.session_id, reason="wake_word_barge_in"))
            return

        # Otherwise launch a new voice session
        cmd = StartSessionCommand(user_id=data.get("user_id", "default_user"))
        await self.execute_command(cmd)

    def _handle_timeout(self, session_id: str, timeout_type: str) -> None:
        """Callback executed when a session watchdog timer expires."""
        self.metrics.total_timeouts += 1
        session = self.session_manager.get_session(session_id)
        if session:
            session.statistics.timeout_count += 1
            if self.state_machine.can_transition_to(SessionState.ERROR):
                self.state_machine.transition_to(SessionState.ERROR, reason=f"Timeout '{timeout_type}'")
            session.state = SessionState.ERROR
