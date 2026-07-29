"""
Master Voice Orchestrator Public API Entrypoint for J.A.R.V.I.S. Phase V1.6.
Exposes start(), stop(), start_session(), cancel_session(), pause(), resume(), get_session(), and get_metrics().
"""
import logging
from typing import Optional, Dict, Any

from .config import OrchestratorConfig, orchestrator_config
from .models import VoiceSession, OrchestratorResult
from .coordinator import OrchestratorCoordinator
from .commands import (
    StartSessionCommand,
    CancelSessionCommand,
    PauseConversationCommand,
    ResumeConversationCommand,
    ResetSessionCommand,
)
from brain.event_bus import event_bus, EventBus

logger = logging.getLogger("JARVIS_VoiceOrchestrator")


class VoiceOrchestrator:
    """
    Production-grade Voice Orchestrator entrypoint.
    Coordinates V1.1 Wake Word, V1.5 Audio Intelligence, V1.2 Speech Recognition,
    V1.3 Conversation Engine, and V1.4 Voice Output Engine without altering their internal logic.
    """

    def __init__(
        self,
        config: Optional[OrchestratorConfig] = None,
        coordinator: Optional[OrchestratorCoordinator] = None,
        bus: Optional[EventBus] = None,
    ):
        self.config = config or orchestrator_config
        self.event_bus = bus or event_bus
        self.coordinator = coordinator or OrchestratorCoordinator(config=self.config, bus=self.event_bus)
        self._running: bool = False

    async def start(self) -> None:
        """Starts the Voice Orchestrator service."""
        self._running = True
        logger.info("[VoiceOrchestrator] Service started successfully.")

    async def stop(self) -> None:
        """Stops the Voice Orchestrator service cleanly."""
        self._running = False
        await self.coordinator.execute_command(ResetSessionCommand())
        logger.info("[VoiceOrchestrator] Service stopped cleanly.")

    async def start_session(self, user_id: str = "default_user", conversation_id: Optional[str] = None) -> OrchestratorResult:
        """Launches a new voice interaction session."""
        cmd = StartSessionCommand(user_id=user_id, conversation_id=conversation_id)
        return await self.coordinator.execute_command(cmd)

    async def cancel_session(self, session_id: str, reason: str = "user_cancellation") -> OrchestratorResult:
        """Cancels an active voice interaction session."""
        cmd = CancelSessionCommand(session_id=session_id, reason=reason)
        return await self.coordinator.execute_command(cmd)

    async def pause(self, session_id: str) -> OrchestratorResult:
        """Pauses target conversation session."""
        cmd = PauseConversationCommand(session_id=session_id)
        return await self.coordinator.execute_command(cmd)

    async def resume(self, session_id: str) -> OrchestratorResult:
        """Resumes target conversation session."""
        cmd = ResumeConversationCommand(session_id=session_id)
        return await self.coordinator.execute_command(cmd)

    def get_session(self, session_id: str) -> Optional[VoiceSession]:
        """Retrieves target VoiceSession entity."""
        return self.coordinator.session_manager.get_session(session_id)

    def get_metrics(self) -> Dict[str, Any]:
        """Returns snapshot summary of orchestrator metrics telemetry."""
        return self.coordinator.metrics.get_summary()

    def get_health(self) -> Dict[str, Any]:
        """Returns status snapshot of all subsystem health monitors."""
        return self.coordinator.health_monitor.get_status()


# Global singleton instance
voice_orchestrator = VoiceOrchestrator()
