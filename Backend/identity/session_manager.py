import time
from typing import Optional, List, Tuple
from identity.identity_models import (
    SessionToken,
    SessionStatus,
    TokenPair
)
from identity.crypto_utils import crypto_utils
from identity.identity_storage import identity_storage
from tools.telemetry import log_structured, backend_log

# Default Token Lifetimes
ACCESS_TOKEN_LIFETIME = 86400        # 24 Hours (1 Day)
REFRESH_TOKEN_LIFETIME = 2592000     # 30 Days

class SessionManager:
    """
    Decoupled Session Manager for issuing, validating, refreshing, and revoking
    session tokens for local identity & multi-device sync sessions.
    """

    def initialize(self) -> None:
        log_structured(backend_log, "INFO", "[SessionManager] Session manager initialized.")

    def issue_session(
        self,
        user_id: str,
        device_id: str,
        ip_address: str = "127.0.0.1",
        user_agent: str = "JARVIS Local Agent"
    ) -> Tuple[TokenPair, SessionToken]:
        """
        Issues a new SessionToken with access_token and refresh_token.
        """
        now = time.time()
        session_id = crypto_utils.generate_uuid("sess")
        access_token = crypto_utils.generate_secure_token("atk")
        refresh_token = crypto_utils.generate_secure_token("rtk")

        expires_at = now + ACCESS_TOKEN_LIFETIME
        refresh_expires_at = now + REFRESH_TOKEN_LIFETIME

        session = SessionToken(
            session_id=session_id,
            user_id=user_id,
            device_id=device_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            refresh_expires_at=refresh_expires_at,
            created_at=now,
            status=SessionStatus.ACTIVE,
            ip_address=ip_address,
            user_agent=user_agent
        )

        identity_storage.save_session_token(session)
        log_structured(backend_log, "INFO", f"[SessionManager] Issued session '{session_id}' for user '{user_id}' on device '{device_id}'")

        token_pair = TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=ACCESS_TOKEN_LIFETIME
        )
        return token_pair, session

    def validate_access_token(self, access_token: str) -> Tuple[bool, Optional[SessionToken], Optional[str]]:
        """
        Validates access token status and expiration timestamp.
        """
        session = identity_storage.get_session_by_access_token(access_token)
        if not session:
            return False, None, "Invalid access token"

        if session.status != SessionStatus.ACTIVE:
            return False, session, f"Session is {session.status.value}"

        if time.time() > session.expires_at:
            session.status = SessionStatus.EXPIRED
            identity_storage.save_session_token(session)
            return False, session, "Access token has expired"

        return True, session, None

    def refresh_session(self, refresh_token: str) -> Tuple[bool, Optional[TokenPair], Optional[str]]:
        """
        Refreshes session access token using valid refresh_token.
        """
        session = identity_storage.get_session_by_refresh_token(refresh_token)
        if not session:
            return False, None, "Invalid refresh token"

        if session.status != SessionStatus.ACTIVE:
            return False, None, f"Session is {session.status.value}"

        now = time.time()
        if now > session.refresh_expires_at:
            session.status = SessionStatus.EXPIRED
            identity_storage.save_session_token(session)
            return False, None, "Refresh token has expired"

        # Generate new access token
        new_access_token = crypto_utils.generate_secure_token("atk")
        session.access_token = new_access_token
        session.expires_at = now + ACCESS_TOKEN_LIFETIME
        identity_storage.save_session_token(session)

        log_structured(backend_log, "INFO", f"[SessionManager] Refreshed session '{session.session_id}'")

        token_pair = TokenPair(
            access_token=new_access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=ACCESS_TOKEN_LIFETIME
        )
        return True, token_pair, None

    def revoke_session(self, session_id: str) -> bool:
        """
        Revokes an active session.
        """
        # Load active session by session_id
        with identity_storage._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM session_tokens WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if not row:
                return False

            conn.execute("UPDATE session_tokens SET status = ? WHERE session_id = ?", (SessionStatus.REVOKED.value, session_id))
            conn.commit()
            log_structured(backend_log, "INFO", f"[SessionManager] Revoked session '{session_id}'")
            return True

    def list_active_sessions(self, user_id: str) -> List[SessionToken]:
        return identity_storage.list_active_sessions(user_id)

session_manager = SessionManager()
