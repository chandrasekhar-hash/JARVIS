"""
Conversation History Manager for J.A.R.V.I.S. Phase V1.6 Voice Orchestrator.
Manages multi-turn conversation accumulation, pruning, and persistence hooks separate from session state.
"""
from typing import Dict, List, Optional
from .interfaces import IConversationHistory
from .models import ConversationTurn


class ConversationHistory(IConversationHistory):
    """
    Manages turn history for voice interaction sessions.
    """

    def __init__(self, max_history_turns: int = 20):
        self.max_history_turns = max_history_turns
        self._history: Dict[str, List[ConversationTurn]] = {}

    def add_turn(self, session_id: str, turn: ConversationTurn) -> None:
        if session_id not in self._history:
            self._history[session_id] = []

        turns = self._history[session_id]
        turns.append(turn)

        # Prune older turns if max limit exceeded
        if len(turns) > self.max_history_turns:
            self._history[session_id] = turns[-self.max_history_turns:]

    def get_history(self, session_id: str) -> List[ConversationTurn]:
        return list(self._history.get(session_id, []))

    def clear_history(self, session_id: str) -> None:
        if session_id in self._history:
            del self._history[session_id]
