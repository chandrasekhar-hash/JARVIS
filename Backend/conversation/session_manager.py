import time
from typing import Dict, Optional, Any
from conversation.models import ConversationSession
from brain.event_bus import event_bus, EventBus
from tools.telemetry import log_structured, backend_log


class SessionManager:
    """
    Manages creation, restoration, expiration, and metadata tracking for multi-turn sessions.
    SLA Target: Session Restore < 30 ms.
    """

    def __init__(self, bus: Optional[EventBus] = None, session_ttl_sec: float = 86400.0):
        self.event_bus = bus or event_bus
        self.session_ttl_sec = session_ttl_sec
        self._sessions: Dict[str, ConversationSession] = {}

    def create_session(self, user_id: str = "default_user") -> ConversationSession:
        session = ConversationSession(user_id=user_id, is_active=True, created_at=time.time())
        self._sessions[session.session_id] = session

        self.event_bus.emit(
            "ConversationStarted",
            session_id=session.session_id,
            user_id=user_id,
        )

        log_structured(
            backend_log,
            "INFO",
            f"[SessionManager] Created new session '{session.session_id}' for user '{user_id}'",
        )
        return session

    def restore_session(self, session_id: str) -> Optional[ConversationSession]:
        """SLA < 30 ms session restoration."""
        start = time.perf_counter()
        session = self._sessions.get(session_id)

        if not session:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            log_structured(backend_log, "WARNING", f"[SessionManager] Session '{session_id}' not found")
            return None

        # Check expiration
        now = time.time()
        if (now - session.last_active_at) > self.session_ttl_sec:
            session.is_active = False
            log_structured(backend_log, "INFO", f"[SessionManager] Session '{session_id}' expired")
            return None

        session.last_active_at = now
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        if elapsed_ms > 30.0:
            log_structured(
                backend_log,
                "WARNING",
                f"[SessionManager] Session restore SLA threshold exceeded: {elapsed_ms:.2f} ms",
            )

        log_structured(
            backend_log,
            "INFO",
            f"[SessionManager] Restored session '{session_id}' in {elapsed_ms:.2f} ms",
        )
        return session

    def end_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session and session.is_active:
            session.is_active = False
            duration_sec = time.time() - session.created_at

            self.event_bus.emit(
                "ConversationEnded",
                session_id=session_id,
                duration_sec=duration_sec,
            )

            log_structured(
                backend_log,
                "INFO",
                f"[SessionManager] Ended session '{session_id}' (Duration: {duration_sec:.1f}s)",
            )
            return True
        return False
