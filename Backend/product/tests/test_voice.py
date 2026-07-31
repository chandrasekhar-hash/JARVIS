"""
JARVIS Product 1.9 - Voice Intelligence Layer Automated Unit & Integration Test Suite.
Verifies Voice Sessions, Wake-Word, VAD, Barge-In Cancelation, Streaming, Intent Routing via P1.5, Notifications, Multilingual Coordination, and Recovery.
"""

import pytest
import os
from backend.product.voice import (
    VoiceEngine,
    VoiceSession,
    VoiceSessionState,
    NotificationPriority,
    IntentCategory,
)
from backend.product.tools import tool_execution_manager_instance
from backend.product.voice.tools.voice_tools import get_voice_tool_metadatas


@pytest.fixture
def temp_db_path(tmp_path):
    return str(tmp_path / "test_voice.db")


@pytest.fixture
def engine(temp_db_path):
    eng = VoiceEngine(db_path=temp_db_path)
    eng.initialize()
    return eng


def test_voice_session_lifecycle(engine):
    session = engine.start_voice_session(owner_id="user_voice_101", language="en")
    assert session.session_id.startswith("vses_")
    assert session.state == VoiceSessionState.IDLE

    # Process voice turn
    turn, audio_stream = engine.process_voice_turn(session_id=session.session_id, user_transcript="Hello JARVIS")
    assert turn.turn_id.startswith("turn_")
    assert turn.intent_category == IntentCategory.CONVERSATIONAL_CHAT
    assert "Hello! I am JARVIS" in turn.system_response_text
    assert session.state == VoiceSessionState.SPEAKING

    chunks = list(audio_stream)
    assert len(chunks) > 0


def test_wake_word_and_vad(engine):
    ww_mgr = engine.wake_word_manager
    detected, conf = ww_mgr.evaluate_audio_frame(b"wake_phrase_marker_audio")
    assert detected is True
    assert conf > 0.85

    not_detected, _ = ww_mgr.evaluate_audio_frame(b"background_noise")
    assert not_detected is False

    vad = engine.vad
    assert vad.is_speech(b"user_speech_audio_frame") is True
    assert vad.is_speech(b"silence_audio_frame") is False


def test_barge_in_playback_cancellation(engine):
    session = engine.start_voice_session(owner_id="user_voice_101")
    
    # Process turn to start SPEAKING state
    turn, audio_stream = engine.process_voice_turn(session_id=session.session_id, user_transcript="Tell me a very long story about AI engines")
    assert session.state == VoiceSessionState.SPEAKING

    # Trigger Barge-In interrupt
    interrupted = engine.trigger_barge_in(session.session_id)
    assert interrupted is True

    # Check remaining audio stream yields 0 or stopped chunks
    remaining_chunks = list(audio_stream)
    assert len(remaining_chunks) == 0 or b"canceled" in b"".join(remaining_chunks)
    assert session.state == VoiceSessionState.LISTENING


def test_intent_router_and_tool_dispatch(engine):
    # 1. Tool execution intent
    cat1, tool1, kwargs1, _ = engine.intent_router.route_transcript("check my slack integration tools", "user_voice_101")
    assert cat1 == IntentCategory.TOOL_EXECUTION
    assert tool1 == "integration_list_connectors"

    # 2. Knowledge RAG intent
    cat2, tool2, kwargs2, _ = engine.intent_router.route_transcript("search knowledge documents for architecture", "user_voice_101")
    assert cat2 == IntentCategory.KNOWLEDGE_RAG
    assert tool2 == "knowledge_search"

    # 3. Automation Workflow intent
    cat3, tool3, kwargs3, _ = engine.intent_router.route_transcript("show my active workflow triggers", "user_voice_101")
    assert cat3 == IntentCategory.AUTOMATION_WORKFLOW
    assert tool3 == "automation_list_workflows"


def test_multilingual_coordination(engine):
    lc = engine.language_coordinator
    lang_es = lc.detect_language(b"spanish_audio_chunk")
    assert lang_es == "es"
    assert lc.get_tts_voice_id("es") == "es_ES-neural-1"

    lang_default = lc.detect_language(b"english_audio_chunk")
    assert lang_default == "en"
    assert lc.get_tts_voice_id("en") == "en_US-neural-1"


def test_voice_notification_priority_queue(engine):
    nm = engine.notification_manager
    nm.quiet_hours_enabled = False

    # Enqueue low priority notification
    res1 = engine.enqueue_voice_notification(owner_id="user_voice_101", message_text="Low priority update", priority=NotificationPriority.LOW)
    assert res1 is True

    # Enqueue urgent priority notification
    res2 = engine.enqueue_voice_notification(owner_id="user_voice_101", message_text="Urgent security alert", priority=NotificationPriority.URGENT)
    assert res2 is True

    # Next notification should be Urgent due to Priority Queue ordering
    next_notif = nm.get_next_notification()
    assert next_notif is not None
    assert next_notif.priority == NotificationPriority.URGENT

    # Test Quiet Hours suppression
    nm.quiet_hours_enabled = True
    res3 = engine.enqueue_voice_notification(owner_id="user_voice_101", message_text="Low update during quiet hours", priority=NotificationPriority.LOW)
    assert res3 is False


def test_voice_tools_registration_with_p15(engine):
    for meta in get_voice_tool_metadatas():
        tool_execution_manager_instance.metadata_registry.register_tool_metadata(meta)

    # 1. Test voice_start_session tool
    start_meta = tool_execution_manager_instance.metadata_registry.get_tool_metadata("voice_start_session")
    assert start_meta is not None
    start_res = start_meta.handler(owner_id="user_test_voice", language="en")
    assert start_res["status"] == "success"
    s_id = start_res["session_id"]

    # 2. Test voice_process_turn tool
    turn_meta = tool_execution_manager_instance.metadata_registry.get_tool_metadata("voice_process_turn")
    turn_res = turn_meta.handler(session_id=s_id, transcript="List my connected workspace tools")
    assert turn_res["status"] == "success"
    assert turn_res["intent_category"] == IntentCategory.TOOL_EXECUTION.value

    # 3. Test voice_trigger_barge_in tool
    barge_meta = tool_execution_manager_instance.metadata_registry.get_tool_metadata("voice_trigger_barge_in")
    barge_res = barge_meta.handler(session_id=s_id)
    assert barge_res["status"] == "success"
    assert barge_res["interrupted"] is True


def test_silence_and_ambiguity_recovery(engine):
    rm = engine.recovery_manager
    silence_prompt = rm.handle_silence_timeout("vses_test_123")
    assert "I'm listening" in silence_prompt

    clarification_prompt = rm.handle_ambiguous_intent("mumbled audio text")
    assert "didn't quite catch that" in clarification_prompt
