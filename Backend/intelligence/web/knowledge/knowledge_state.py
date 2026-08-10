"""
Ephemeral Scope Isolation & Memory Session Manager for J.A.R.V.I.S. I2.2 V9.
"""
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from intelligence.web.knowledge.knowledge_graph import BoundedKnowledgeGraph


@dataclass
class KnowledgeSession:
    session_id: str
    owner_scope_id: str
    conversation_id: str
    created_at: float
    last_accessed: float
    graph: BoundedKnowledgeGraph = field(default_factory=BoundedKnowledgeGraph)


class KnowledgeStateManager:
    """
    Manages owner-scoped, conversation-scoped, request-isolated ephemeral session states
    with automatic TTL expiration and bounded eviction. No webpage bodies are stored.
    """

    TTL_SECONDS = 3600.0
    MAX_SESSIONS_PER_CONVERSATION = 5

    def __init__(self):
        # Key: (owner_scope_id, conversation_id, session_id) -> KnowledgeSession
        self._sessions: Dict[Tuple[str, str, str], KnowledgeSession] = {}

    def get_or_create_session(
        self,
        owner_scope_id: Optional[str],
        conversation_id: Optional[str],
        session_id: str,
    ) -> KnowledgeSession:
        self.evict_expired_sessions()

        owner_key = owner_scope_id or "global_owner"
        conv_key = conversation_id or "default_conversation"
        key = (owner_key, conv_key, session_id)

        now = time.time()
        if key in self._sessions:
            session = self._sessions[key]
            session.last_accessed = now
            return session

        # Enforce max sessions per conversation limit
        conv_sessions = [
            (k, s) for k, s in self._sessions.items() if k[0] == owner_key and k[1] == conv_key
        ]
        if len(conv_sessions) >= self.MAX_SESSIONS_PER_CONVERSATION:
            # Evict oldest by last_accessed
            conv_sessions.sort(key=lambda item: item[1].last_accessed)
            oldest_key, _ = conv_sessions[0]
            del self._sessions[oldest_key]

        session = KnowledgeSession(
            session_id=session_id,
            owner_scope_id=owner_key,
            conversation_id=conv_key,
            created_at=now,
            last_accessed=now,
        )
        self._sessions[key] = session
        return session

    def evict_expired_sessions(self):
        now = time.time()
        expired_keys = [
            k
            for k, session in self._sessions.items()
            if (now - session.last_accessed) > self.TTL_SECONDS
        ]
        for k in expired_keys:
            del self._sessions[k]

    def clear_all(self):
        self._sessions.clear()


knowledge_state_manager = KnowledgeStateManager()
