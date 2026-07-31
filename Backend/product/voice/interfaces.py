"""
JARVIS Product 1.9 - Voice Intelligence Interfaces.

Defines abstract contracts for Session Management, Wake-Word, VAD, Streaming, Barge-In, Intent Routing, and Notifications.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from .models import (
    VoiceSession,
    VoiceSessionState,
    ConversationTurn,
    VoiceNotification,
    IntentCategory,
)


class IVoiceSessionManager(ABC):
    @abstractmethod
    def start_session(self, owner_id: str, language: str = "en") -> VoiceSession:
        pass

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[VoiceSession]:
        pass

    @abstractmethod
    def update_state(self, session_id: str, new_state: VoiceSessionState) -> VoiceSessionState:
        pass


class IWakeWordManager(ABC):
    @abstractmethod
    def evaluate_audio_frame(self, audio_chunk: bytes) -> Tuple[bool, float]:
        pass


class IVoiceActivityDetector(ABC):
    @abstractmethod
    def is_speech(self, audio_chunk: bytes) -> bool:
        pass


class IBargeInManager(ABC):
    @abstractmethod
    def trigger_barge_in(self, session_id: str) -> bool:
        pass


class IIntentRouter(ABC):
    @abstractmethod
    def route_transcript(self, transcript: str, owner_id: str) -> Tuple[IntentCategory, Optional[str], Dict[str, Any]]:
        pass


class IVoiceNotificationManager(ABC):
    @abstractmethod
    def enqueue_notification(self, notification: VoiceNotification) -> bool:
        pass
