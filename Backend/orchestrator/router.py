"""
Event Router for J.A.R.V.I.S. Phase V1.6 Voice Orchestrator.
Subscribes to subsystem EventBus events and dispatches notifications to OrchestratorCoordinator.
"""
import logging
from typing import Any, Callable, Optional
from brain.event_bus import event_bus, EventBus

logger = logging.getLogger("JARVIS_EventRouter")


class EventRouter:
    """
    Subscribes to events across V1.1–V1.5 subsystems and maps them to Coordinator handlers.
    """

    EVENT_SUBSCRIPTIONS = [
        "WakeWordDetected",
        "AudioInputReceived",
        "EnhancedAudioReady",
        "SpeechRecognitionStarted",
        "TranscriptReady",
        "speech_final",
        "ConversationResponseReady",
        "SpeechPlaybackStarted",
        "SpeechPlaybackCompleted",
        "SpeechPlaybackCancelled",
        "SpeechPlaybackError",
    ]

    def __init__(self, coordinator_handler: Callable, bus: Optional[EventBus] = None):
        self.coordinator_handler = coordinator_handler
        self.event_bus = bus or event_bus
        self.subscribe_all()

    def subscribe_all(self) -> None:
        for event_name in self.EVENT_SUBSCRIPTIONS:
            try:
                self.event_bus.subscribe(event_name, self._create_listener(event_name))
            except Exception as e:
                logger.warning(f"[EventRouter] Could not subscribe to '{event_name}': {e}")

    def _create_listener(self, event_name: str) -> Callable:
        def _listener(event: Any = None, **kwargs):
            data = event.data if hasattr(event, "data") else (event if isinstance(event, dict) else kwargs)
            self.coordinator_handler(event_name, data)
        return _listener
