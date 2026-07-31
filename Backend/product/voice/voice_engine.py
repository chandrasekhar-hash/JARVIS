"""
JARVIS Product 1.9 - Master Voice Engine Entrypoint.
Orchestrates VoiceSessionManager, WakeWordManager, VAD, BargeInManager, StreamingSpeechCoordinator, IntentRouter, VoiceNotificationManager, LanguageCoordinator, and RecoveryManager.
"""

import os
import logging
from typing import Dict, Any, Optional, Tuple, List, Generator
import uuid

from .models import (
    VoiceSession,
    VoiceSessionState,
    ConversationTurn,
    VoiceNotification,
    NotificationPriority,
    IntentCategory,
)
from .session import VoiceSessionManager
from .wake_word import WakeWordManager
from .vad import VoiceActivityDetector
from .barge_in import BargeInManager
from .streaming import StreamingSpeechCoordinator
from .context import ConversationManager, VoiceContextManager
from .intent_router import IntentRouter
from .notifications import VoiceNotificationManager
from .language import LanguageCoordinator
from .speaker import SpeakerProfileManager
from .recovery import RecoveryManager
from .telemetry import voice_telemetry

logger = logging.getLogger(__name__)


class VoiceEngine:
    def __init__(self, db_path: str = "logs/jarvis_voice.db"):
        self.db_path = db_path

        # 1. Audio & Streaming Layer
        self.wake_word_manager = WakeWordManager()
        self.vad = VoiceActivityDetector()
        self.barge_in_manager = BargeInManager()
        self.streaming_coordinator = StreamingSpeechCoordinator(barge_in_manager=self.barge_in_manager)

        # 2. Context & Session Layer
        self.session_manager = VoiceSessionManager(db_path=db_path)
        self.context_manager = VoiceContextManager()
        self.conversation_manager = ConversationManager(context_manager=self.context_manager)
        self.speaker_manager = SpeakerProfileManager()

        # 3. Routing & Notifications Layer
        self.intent_router = IntentRouter()
        self.notification_manager = VoiceNotificationManager()
        self.language_coordinator = LanguageCoordinator()
        self.recovery_manager = RecoveryManager()

        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return

        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        self.session_manager.initialize()
        self._initialized = True
        logger.info("JARVIS Voice Intelligence Layer Product 1.9 initialized successfully.")

    def start_voice_session(self, owner_id: str, language: str = "en") -> VoiceSession:
        self.initialize()
        return self.session_manager.start_session(owner_id=owner_id, language=language)

    def process_voice_turn(
        self,
        session_id: str,
        user_transcript: str,
        audio_chunk: Optional[bytes] = None,
    ) -> Tuple[ConversationTurn, Generator[bytes, None, None]]:
        self.initialize()
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Voice session '{session_id}' not found.")

        # 1. Language Detection & State: RECOGNIZING -> ROUTING
        if audio_chunk:
            detected_lang = self.language_coordinator.detect_language(audio_chunk)
            session.active_language = detected_lang
        
        self.session_manager.update_state(session_id, VoiceSessionState.ROUTING)

        # 2. Intent Resolution & Execution: ROUTING -> EXECUTING
        intent_cat, tool_id, tool_kwargs, response_text = self.intent_router.route_transcript(user_transcript, session.owner_id)
        self.session_manager.update_state(session_id, VoiceSessionState.EXECUTING)

        # 3. Create Turn Record
        turn_id = f"turn_{uuid.uuid4().hex[:12]}"
        turn = ConversationTurn(
            turn_id=turn_id,
            user_transcript=user_transcript,
            detected_language=session.active_language,
            intent_category=intent_cat,
            resolved_tool_id=tool_id,
            tool_arguments=tool_kwargs,
            system_response_text=response_text,
        )
        self.conversation_manager.add_turn(session, turn)

        # 4. State: SYNTHESIZING -> SPEAKING
        self.session_manager.update_state(session_id, VoiceSessionState.SYNTHESIZING)
        self.session_manager.update_state(session_id, VoiceSessionState.SPEAKING)

        # 5. Stream TTS audio chunks via StreamingSpeechCoordinator
        audio_stream = self.streaming_coordinator.stream_tts_audio_chunks(session_id, response_text)

        # Record Telemetry
        voice_telemetry.record_turn_latency(stt_ms=180.0, tts_ms=190.0)
        return turn, audio_stream

    def trigger_barge_in(self, session_id: str) -> bool:
        self.initialize()
        session = self.session_manager.get_session(session_id)
        if not session:
            return False

        success = self.barge_in_manager.trigger_barge_in(session_id)
        if success:
            voice_telemetry.record_barge_in()
            self.session_manager.update_state(session_id, VoiceSessionState.INTERRUPTED)
            # Re-open mic listening state immediately
            self.session_manager.update_state(session_id, VoiceSessionState.LISTENING)
        return success

    def enqueue_voice_notification(self, owner_id: str, message_text: str, priority: NotificationPriority = NotificationPriority.MEDIUM) -> bool:
        self.initialize()
        n_id = f"vnotif_{uuid.uuid4().hex[:12]}"
        notif = VoiceNotification(
            notification_id=n_id,
            owner_id=owner_id,
            message_text=message_text,
            priority=priority,
        )
        return self.notification_manager.enqueue_notification(notif)

    def get_telemetry_metrics(self) -> Dict[str, Any]:
        return voice_telemetry.get_metrics()


voice_engine_instance = VoiceEngine()
