"""
Product Engine Public API Entrypoint for J.A.R.V.I.S. Phase P1.1 (Identity & User Management).
Exposes production-grade high-level APIs for authentication, profiles, sessions, preferences, security, and metrics telemetry.
"""
import logging
from typing import Optional, Dict, Any, List, Tuple

from .config import ProductConfig, product_config
from .models import (
    User,
    Role,
    UserProfile,
    UserPreferences,
    Session,
    AuthResult,
    SecurityContext,
)
from .coordinator import ProductCoordinator
from brain.event_bus import event_bus, EventBus

logger = logging.getLogger("JARVIS_ProductEngine")


class ProductEngine:
    """
    Production-grade Product Layer Entrypoint for Phase P1.1 Identity & User Management.
    Coordinates User Profiles, Sessions, Authentication, Security, and User Preferences
    without altering existing V1.1-V1.8 Core Engine APIs.
    """

    def __init__(
        self,
        config: Optional[ProductConfig] = None,
        coordinator: Optional[ProductCoordinator] = None,
        bus: Optional[EventBus] = None,
    ):
        self.config = config or product_config
        self.event_bus = bus or event_bus
        self.coordinator = coordinator or ProductCoordinator(config=self.config, bus=self.event_bus)
        self._running: bool = False

    async def start(self) -> None:
        """Starts the Product Engine service."""
        self._running = True
        logger.info("[ProductEngine] Identity & User Management service started successfully.")

    async def stop(self) -> None:
        """Stops the Product Engine service cleanly."""
        self._running = False
        logger.info("[ProductEngine] Identity & User Management service stopped cleanly.")

    def register_user(
        self,
        username: str,
        email: str,
        password: str,
        display_name: Optional[str] = None,
        role: Role = Role.USER,
        avatar: str = "",
        language_preference: str = "en-US",
        time_zone: str = "UTC",
        theme_preference: str = "dark",
    ) -> AuthResult:
        """Registers a new user account with initial profile and preferences."""
        return self.coordinator.register_user(
            username=username,
            email=email,
            password=password,
            display_name=display_name,
            role=role,
            avatar=avatar,
            language_preference=language_preference,
            time_zone=time_zone,
            theme_preference=theme_preference,
        )

    def login(
        self,
        identifier: str,
        password: str,
        device_id: str = "default_device",
        device_name: str = "Desktop Client",
        ip_address: str = "127.0.0.1",
        remember_me: bool = False,
    ) -> AuthResult:
        """Authenticates user credentials and opens an active session."""
        return self.coordinator.login(
            identifier=identifier,
            password=password,
            device_id=device_id,
            device_name=device_name,
            ip_address=ip_address,
            remember_me=remember_me,
        )

    def logout(self, session_token: str) -> bool:
        """Logs out user and revokes active session token."""
        return self.coordinator.logout(session_token)

    def validate_session(self, session_token: str) -> AuthResult:
        """Validates active session token."""
        return self.coordinator.validate_session(session_token)

    def login_with_remember_token(
        self,
        remember_me_token: str,
        device_id: str = "default_device",
        ip_address: str = "127.0.0.1",
    ) -> AuthResult:
        """Restores session via persistent remember-me token."""
        return self.coordinator.login_with_remember_token(
            remember_me_token=remember_me_token,
            device_id=device_id,
            ip_address=ip_address,
        )

    def request_password_reset(self, identifier: str) -> Tuple[bool, str]:
        """Generates a password reset token."""
        return self.coordinator.request_password_reset(identifier)

    def confirm_password_reset(self, reset_token: str, new_password: str) -> Tuple[bool, str]:
        """Confirms password reset request with new password."""
        return self.coordinator.confirm_password_reset(reset_token, new_password)

    def change_password(self, user_id: str, current_password: str, new_password: str) -> Tuple[bool, str]:
        """Changes password for an authenticated user."""
        return self.coordinator.auth_service.change_password(user_id, current_password, new_password)

    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Retrieves user profile metadata."""
        return self.coordinator.get_profile(user_id)

    def update_profile(
        self,
        user_id: str,
        display_name: Optional[str] = None,
        email: Optional[str] = None,
        avatar: Optional[str] = None,
        language_preference: Optional[str] = None,
        time_zone: Optional[str] = None,
        theme_preference: Optional[str] = None,
    ) -> UserProfile:
        """Updates profile metadata fields."""
        return self.coordinator.update_profile(
            user_id=user_id,
            display_name=display_name,
            email=email,
            avatar=avatar,
            language_preference=language_preference,
            time_zone=time_zone,
            theme_preference=theme_preference,
        )

    def get_preferences(self, user_id: str) -> UserPreferences:
        """Retrieves user preferences."""
        return self.coordinator.get_preferences(user_id)

    def update_preferences(
        self,
        user_id: str,
        **kwargs,
    ) -> UserPreferences:
        """Updates user preferences."""
        return self.coordinator.update_preferences(user_id, **kwargs)

    def get_active_sessions(self, user_id: str) -> List[Session]:
        """Returns active sessions for target user."""
        return self.coordinator.get_active_sessions(user_id)

    def revoke_session(self, session_id: str) -> bool:
        """Revokes a specific session by ID."""
        return self.coordinator.revoke_session(session_id)

    def get_security_context(self, session_token: Optional[str] = None) -> SecurityContext:
        """Constructs SecurityContext from active session token."""
        return self.coordinator.get_security_context(session_token)

    def get_metrics(self) -> Dict[str, Any]:
        """Returns summary of product layer operational metrics."""
        return {
            "status": "online" if self._running else "stopped",
            "db_path": self.config.db_path,
            "session_timeout_seconds": self.config.session_timeout_seconds,
            "remember_me_expiration_seconds": self.config.remember_me_expiration_seconds,
            "max_failed_login_attempts": self.config.max_failed_login_attempts,
        }

    def get_health(self) -> Dict[str, Any]:
        """Returns subsystem health snapshot."""
        return {
            "healthy": self._running,
            "subsystem": "ProductLayer.Identity",
            "phase": "P1.1",
        }


# Global singleton instance
product_engine = ProductEngine()
