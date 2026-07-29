"""
Session Manager Service for J.A.R.V.I.S. Product Layer (Phase P1.1).
Handles session tokens, remember-me persistent tokens, sliding window timeout, and multi-device tracking.
"""
import time
import logging
from typing import Optional, List, Tuple

from .config import ProductConfig, product_config
from .models import Session
from .interfaces import ISessionRepository, ITokenGenerator
from .security import TokenGenerator

logger = logging.getLogger("JARVIS_SessionManager")


class SessionManager:
    """
    Session Management domain service.
    Orchestrates session creation, active token validation, sliding expiration, and device revocation.
    """

    def __init__(
        self,
        repository: ISessionRepository,
        token_generator: Optional[ITokenGenerator] = None,
        config: Optional[ProductConfig] = None,
    ):
        self.repository = repository
        self.token_generator = token_generator or TokenGenerator()
        self.config = config or product_config

    def create_session(
        self,
        user_id: str,
        device_id: str = "default_device",
        device_name: str = "Desktop Client",
        ip_address: str = "127.0.0.1",
        remember_me: bool = False,
        custom_timeout: Optional[int] = None,
    ) -> Session:
        """
        Creates and persists a new Session with unique tokens.
        Enforces maximum active session limits per user.
        """
        now = time.time()
        timeout = custom_timeout or self.config.session_timeout_seconds
        expires_at = now + timeout

        session_id = self.token_generator.generate_uuid(prefix="ses")
        token = self.token_generator.generate_token(prefix="stk")

        remember_me_token = None
        if remember_me:
            remember_me_token = self.token_generator.generate_token(prefix="rmt")
            expires_at = now + self.config.remember_me_expiration_seconds

        active_sessions = self.repository.get_user_sessions(user_id)
        if len(active_sessions) >= self.config.max_active_sessions_per_user:
            oldest = active_sessions[-1]
            self.repository.revoke_session(oldest.session_id)
            logger.info(
                f"[SessionManager] Revoked oldest session '{oldest.session_id}' for user '{user_id}' due to session cap."
            )

        session = Session(
            session_id=session_id,
            user_id=user_id,
            token=token,
            remember_me_token=remember_me_token,
            device_id=device_id,
            device_name=device_name,
            ip_address=ip_address,
            created_at=now,
            expires_at=expires_at,
            last_accessed_at=now,
            is_active=True,
        )
        return self.repository.create_session(session)

    def validate_session_token(self, token: str) -> Optional[Session]:
        """
        Validates active session token.
        Extends session expiration if sliding window is enabled.
        """
        if not token:
            return None

        session = self.repository.get_session_by_token(token)
        if not session:
            return None

        now = time.time()
        if session.is_expired(current_time=now):
            self.repository.revoke_session(session.session_id)
            return None

        session.last_accessed_at = now
        if self.config.session_sliding_window and not session.remember_me_token:
            session.expires_at = now + self.config.session_timeout_seconds

        return self.repository.update_session(session)

    def validate_remember_token(self, remember_me_token: str) -> Optional[Session]:
        """Validates persistent remember-me token and returns session if active."""
        if not remember_me_token:
            return None

        session = self.repository.get_session_by_remember_token(remember_me_token)
        if not session:
            return None

        now = time.time()
        if session.is_expired(current_time=now):
            self.repository.revoke_session(session.session_id)
            return None

        return session

    def get_user_active_sessions(self, user_id: str) -> List[Session]:
        """Retrieves all active sessions for a user ID."""
        return self.repository.get_user_sessions(user_id)

    def revoke_session(self, session_id: str) -> bool:
        """Revokes a session by session ID."""
        return self.repository.revoke_session(session_id)

    def revoke_session_by_token(self, token: str) -> bool:
        """Revokes session associated with a session token."""
        session = self.repository.get_session_by_token(token)
        if session:
            return self.repository.revoke_session(session.session_id)
        return False

    def revoke_all_user_sessions(self, user_id: str) -> int:
        """Revokes all active sessions for a user ID."""
        return self.repository.revoke_all_user_sessions(user_id)
