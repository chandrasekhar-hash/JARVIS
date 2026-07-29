"""
Session Manager for J.A.R.V.I.S. Phase V1.6 Voice Orchestrator.
Manages VoiceSession lifecycle entities, active session registries, pausing, resuming, and cancellation.
"""
import logging
from typing import Dict, Optional, List
from .interfaces import ISessionManager
from .models import VoiceSession, SessionState
from .config import orchestrator_config

logger = logging.getLogger("JARVIS_SessionManager")


class SessionManager(ISessionManager):
    """
    Manages active voice sessions and their lifecycle entities.
    """

    def __init__(self, max_sessions: int = 100):
        self.max_sessions = max_sessions
        self._sessions: Dict[str, VoiceSession] = {}
        self._active_session_id: Optional[str] = None

    def create_session(self, user_id: str = "default_user", conversation_id: Optional[str] = None) -> VoiceSession:
        if len(self._sessions) >= self.max_sessions:
            # Clean up oldest inactive sessions
            oldest = list(self._sessions.keys())[0]
            del self._sessions[oldest]

        session = VoiceSession(user_id=user_id)
        if conversation_id:
            session.conversation_id = conversation_id

        self._sessions[session.session_id] = session
        self._active_session_id = session.session_id
        logger.info(f"[SessionManager] Created session '{session.session_id}' for user '{user_id}'.")
        return session

    def get_session(self, session_id: str) -> Optional[VoiceSession]:
        return self._sessions.get(session_id)

    def get_active_session(self) -> Optional[VoiceSession]:
        if self._active_session_id:
            return self._sessions.get(self._active_session_id)
        return None

    def pause_session(self, session_id: str) -> bool:
        session = self.get_session(session_id)
        if session:
            session.state = SessionState.PAUSED
            return True
        return False

    def resume_session(self, session_id: str) -> bool:
        session = self.get_session(session_id)
        if session:
            session.state = SessionState.LISTENING
            return True
        return False

    def cancel_session(self, session_id: str, reason: str = "") -> bool:
        session = self.get_session(session_id)
        if session:
            session.state = SessionState.CANCELLED
            session.statistics.cancellation_count += 1
            return True
        return False

    def destroy_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            if self._active_session_id == session_id:
                self._active_session_id = None
            return True
        return False
