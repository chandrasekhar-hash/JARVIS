"""
JARVIS Product 1.9 - Voice Intelligence Domain Models.

Defines data classes, enums, turn metadata, voice notification priority queues, and session states.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, IntEnum
from typing import List, Dict, Any, Optional
import uuid


class VoiceSessionState(str, Enum):
    IDLE = "IDLE"
    WAKE_WORD_DETECTED = "WAKE_WORD_DETECTED"
    LISTENING = "LISTENING"
    RECOGNIZING = "RECOGNIZING"
    ROUTING = "ROUTING"
    EXECUTING = "EXECUTING"
    SYNTHESIZING = "SYNTHESIZING"
    SPEAKING = "SPEAKING"
    INTERRUPTED = "INTERRUPTED"
    ERROR = "ERROR"


class IntentCategory(str, Enum):
    TOOL_EXECUTION = "TOOL_EXECUTION"
    KNOWLEDGE_RAG = "KNOWLEDGE_RAG"
    AUTOMATION_WORKFLOW = "AUTOMATION_WORKFLOW"
    CONVERSATIONAL_CHAT = "CONVERSATIONAL_CHAT"
    UNKNOWN = "UNKNOWN"


class NotificationPriority(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


@dataclass
class ConversationTurn:
    turn_id: str
    user_transcript: str
    detected_language: str = "en"
    intent_category: IntentCategory = IntentCategory.CONVERSATIONAL_CHAT
    resolved_tool_id: Optional[str] = None
    tool_arguments: Dict[str, Any] = field(default_factory=dict)
    system_response_text: str = ""
    was_interrupted: bool = False
    interrupted_at_char: int = 0
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "user_transcript": self.user_transcript,
            "detected_language": self.detected_language,
            "intent_category": self.intent_category.value,
            "resolved_tool_id": self.resolved_tool_id,
            "tool_arguments": self.tool_arguments,
            "system_response_text": self.system_response_text,
            "was_interrupted": self.was_interrupted,
            "interrupted_at_char": self.interrupted_at_char,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class VoiceNotification:
    notification_id: str
    owner_id: str
    message_text: str
    priority: NotificationPriority = NotificationPriority.MEDIUM
    source_subsystem: str = "P1.7_automation"
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SpeakerProfile:
    speaker_id: str
    owner_id: str
    display_name: str
    preferred_language: str = "en"
    preferred_voice_id: str = "en_US-neural-1"


@dataclass
class VoiceSession:
    session_id: str
    owner_id: str
    active_language: str = "en"
    state: VoiceSessionState = VoiceSessionState.IDLE
    wake_word_confidence: float = 0.0
    turns: List[ConversationTurn] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create_new(cls, owner_id: str, language: str = "en") -> "VoiceSession":
        s_id = f"vses_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow()
        return cls(
            session_id=s_id,
            owner_id=owner_id,
            active_language=language,
            state=VoiceSessionState.IDLE,
            created_at=now,
            updated_at=now,
        )
