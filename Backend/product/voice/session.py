"""
JARVIS Product 1.9 - Voice Session Manager.
Master coordinator managing voice session lifecycles, states, and turn tracking.
"""

import sqlite3
import json
import logging
import uuid
from typing import Dict, Any, Optional, List
from .interfaces import IVoiceSessionManager
from .models import VoiceSession, VoiceSessionState, ConversationTurn, IntentCategory
from .logging import voice_logger
from .telemetry import voice_telemetry

logger = logging.getLogger(__name__)


class VoiceSessionManager(IVoiceSessionManager):
    def __init__(self, db_path: str = "logs/jarvis_voice.db"):
        self.db_path = db_path
        self._active_sessions: Dict[str, VoiceSession] = {}

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        conn = self._get_connection()
        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS voice_sessions (
                        session_id TEXT PRIMARY KEY,
                        owner_id TEXT NOT NULL,
                        active_language TEXT NOT NULL,
                        state TEXT NOT NULL,
                        wake_word_confidence REAL NOT NULL,
                        turns_json TEXT,
                        metadata_json TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
        finally:
            conn.close()

    def start_session(self, owner_id: str, language: str = "en") -> VoiceSession:
        session = VoiceSession.create_new(owner_id=owner_id, language=language)
        self._active_sessions[session.session_id] = session
        voice_telemetry.record_session()
        voice_logger.log_event("VOICE_SESSION_STARTED", session.session_id, owner_id)

        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO voice_sessions (
                        session_id, owner_id, active_language, state, wake_word_confidence,
                        turns_json, metadata_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session.session_id,
                        session.owner_id,
                        session.active_language,
                        session.state.value,
                        session.wake_word_confidence,
                        json.dumps([t.to_dict() for t in session.turns]),
                        json.dumps(session.metadata),
                        session.created_at.isoformat(),
                        session.updated_at.isoformat(),
                    ),
                )
        finally:
            conn.close()

        return session

    def get_session(self, session_id: str) -> Optional[VoiceSession]:
        if session_id in self._active_sessions:
            return self._active_sessions[session_id]

        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT * FROM voice_sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            from datetime import datetime
            session = VoiceSession(
                session_id=row["session_id"],
                owner_id=row["owner_id"],
                active_language=row["active_language"],
                state=VoiceSessionState(row["state"]),
                wake_word_confidence=row["wake_word_confidence"],
                metadata=json.loads(row["metadata_json"]) if row["metadata_json"] else {},
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            self._active_sessions[session.session_id] = session
            return session
        finally:
            conn.close()

    def update_state(self, session_id: str, new_state: VoiceSessionState) -> VoiceSessionState:
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Voice session '{session_id}' not found.")

        old_state = session.state
        session.state = new_state
        logger.info(f"[VoiceSessionManager] Session '{session_id}' state: {old_state.value} -> {new_state.value}")
        voice_logger.log_event("VOICE_SESSION_STATE_CHANGED", session_id, session.owner_id, {"old_state": old_state.value, "new_state": new_state.value})
        return new_state
