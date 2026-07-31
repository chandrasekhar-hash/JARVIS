"""
JARVIS Product 1.9 - Voice Intelligence Layer.
"""

from .models import (
    VoiceSession,
    VoiceSessionState,
    ConversationTurn,
    VoiceNotification,
    NotificationPriority,
    SpeakerProfile,
    IntentCategory,
)
from .voice_engine import VoiceEngine, voice_engine_instance
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

__all__ = [
    "VoiceSession",
    "VoiceSessionState",
    "ConversationTurn",
    "VoiceNotification",
    "NotificationPriority",
    "SpeakerProfile",
    "IntentCategory",
    "VoiceEngine",
    "voice_engine_instance",
    "VoiceSessionManager",
    "WakeWordManager",
    "VoiceActivityDetector",
    "BargeInManager",
    "StreamingSpeechCoordinator",
    "ConversationManager",
    "VoiceContextManager",
    "IntentRouter",
    "VoiceNotificationManager",
    "LanguageCoordinator",
    "SpeakerProfileManager",
    "RecoveryManager",
]
