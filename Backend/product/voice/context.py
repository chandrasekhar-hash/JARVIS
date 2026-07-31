"""
JARVIS Product 1.9 - Voice Context & Conversation Manager.
Maintains short-term conversational context, multi-turn history, slot fills, and user turn tracking.
"""

import logging
from typing import List, Dict, Any, Optional
from .models import VoiceSession, ConversationTurn

logger = logging.getLogger(__name__)


class VoiceContextManager:
    def __init__(self):
        self._active_slots: Dict[str, Dict[str, Any]] = {}

    def set_slot(self, session_id: str, key: str, value: Any) -> None:
        if session_id not in self._active_slots:
            self._active_slots[session_id] = {}
        self._active_slots[session_id][key] = value

    def get_slots(self, session_id: str) -> Dict[str, Any]:
        return self._active_slots.get(session_id, {})


class ConversationManager:
    def __init__(self, context_manager: VoiceContextManager):
        self.context_manager = context_manager

    def add_turn(self, session: VoiceSession, turn: ConversationTurn) -> None:
        session.turns.append(turn)
        logger.info(f"[ConversationManager] Added turn '{turn.turn_id}' (User: '{turn.user_transcript[:20]}...') to session '{session.session_id}'.")
