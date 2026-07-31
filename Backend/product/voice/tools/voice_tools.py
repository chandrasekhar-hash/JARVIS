"""
JARVIS Product 1.9 - Voice Intelligence Tools.
Exposes Voice Intelligence capabilities to Product 1.5 Tool Execution Engine.
"""

from typing import List, Dict, Any
from ...tools import ToolMetadata, ToolCategory, ToolCapability
from ..models import NotificationPriority


def voice_start_session_handler(owner_id: str = "default_user", language: str = "en", **kwargs) -> Dict[str, Any]:
    from ..voice_engine import voice_engine_instance
    session = voice_engine_instance.start_voice_session(owner_id=owner_id, language=language)
    return {
        "status": "success",
        "session_id": session.session_id,
        "owner_id": session.owner_id,
        "session_state": session.state.value,
        "language": session.active_language,
    }


def voice_process_turn_handler(session_id: str, transcript: str, **kwargs) -> Dict[str, Any]:
    from ..voice_engine import voice_engine_instance
    turn, stream = voice_engine_instance.process_voice_turn(session_id=session_id, user_transcript=transcript)
    chunks_count = len(list(stream))
    return {
        "status": "success",
        "turn_id": turn.turn_id,
        "session_id": session_id,
        "intent_category": turn.intent_category.value,
        "resolved_tool_id": turn.resolved_tool_id,
        "response_text": turn.system_response_text,
        "audio_chunks_count": chunks_count,
    }


def voice_trigger_barge_in_handler(session_id: str, **kwargs) -> Dict[str, Any]:
    from ..voice_engine import voice_engine_instance
    success = voice_engine_instance.trigger_barge_in(session_id=session_id)
    return {
        "status": "success" if success else "failed",
        "session_id": session_id,
        "interrupted": success,
    }


def voice_enqueue_notification_handler(message_text: str, owner_id: str = "default_user", priority: int = 2, **kwargs) -> Dict[str, Any]:
    from ..voice_engine import voice_engine_instance
    p_enum = NotificationPriority(priority)
    success = voice_engine_instance.enqueue_voice_notification(owner_id=owner_id, message_text=message_text, priority=p_enum)
    return {
        "status": "success" if success else "suppressed",
        "message": message_text,
        "priority": p_enum.name,
    }


def get_voice_tool_metadatas() -> List[ToolMetadata]:
    return [
        ToolMetadata(
            tool_id="voice_start_session",
            name="Start Voice Session",
            description="Initializes a real-time voice conversation session for a user.",
            category=ToolCategory.COMMUNICATION,
            capabilities=[ToolCapability.FILESYSTEM_WRITE.value],
            safety_level="safe",
            input_schema={
                "type": "object",
                "properties": {
                    "owner_id": {"type": "string"},
                    "language": {"type": "string"},
                },
            },
            handler=voice_start_session_handler,
            owner="voice_intelligence",
        ),
        ToolMetadata(
            tool_id="voice_process_turn",
            name="Process Voice Turn",
            description="Processes a spoken transcript turn, routes intent via P1.5, and synthesizes audio response.",
            category=ToolCategory.COMMUNICATION,
            capabilities=[ToolCapability.NETWORK_OUTBOUND.value],
            safety_level="safe",
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "transcript": {"type": "string"},
                },
                "required": ["session_id", "transcript"],
            },
            handler=voice_process_turn_handler,
            owner="voice_intelligence",
        ),
        ToolMetadata(
            tool_id="voice_trigger_barge_in",
            name="Trigger Voice Barge-In",
            description="Instantly interrupts active speech output and flushes playback audio buffers.",
            category=ToolCategory.COMMUNICATION,
            capabilities=[ToolCapability.SYSTEM_EXECUTE.value],
            safety_level="safe",
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                },
                "required": ["session_id"],
            },
            handler=voice_trigger_barge_in_handler,
            owner="voice_intelligence",
        ),
        ToolMetadata(
            tool_id="voice_enqueue_notification",
            name="Enqueue Spoken Notification",
            description="Queues a spoken audio alert notification for the user.",
            category=ToolCategory.COMMUNICATION,
            capabilities=[ToolCapability.FILESYSTEM_WRITE.value],
            safety_level="safe",
            input_schema={
                "type": "object",
                "properties": {
                    "message_text": {"type": "string"},
                    "owner_id": {"type": "string"},
                    "priority": {"type": "integer"},
                },
                "required": ["message_text"],
            },
            handler=voice_enqueue_notification_handler,
            owner="voice_intelligence",
        ),
    ]
