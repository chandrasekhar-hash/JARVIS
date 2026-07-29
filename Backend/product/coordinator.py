"""
Product Layer Coordinator for J.A.R.V.I.S. (Phase P1.1).
Orchestrates workflows across Authentication, User Management, Profiles, Sessions, Preferences, Security,
Security Audit Logging, and broadcasts domain events via EventBus to integrate seamlessly with V1.1-V1.8 core engines.
"""
import logging
from typing import Optional, Dict, Any, List

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
from .users import UserManager
from .profiles import ProfileManager
from .sessions import SessionManager
from .preferences import PreferenceManager
from .authentication import AuthenticationService
from .storage import SQLiteProductStorage
from .security import SecurityProvider
from .audit import SecurityAuditLogger
from brain.event_bus import event_bus, EventBus

logger = logging.getLogger("JARVIS_ProductCoordinator")


class ProductCoordinator:
    """
    Coordinator pattern implementation for J.A.R.V.I.S. Product Layer.
    Encapsulates sub-service dependencies, audit logging, event dispatching, and cross-cutting security checks.
    """

    def __init__(
        self,
        config: Optional[ProductConfig] = None,
        storage: Optional[SQLiteProductStorage] = None,
        bus: Optional[EventBus] = None,
    ):
        self.config = config or product_config
        self.storage = storage or SQLiteProductStorage(config=self.config)
        self.event_bus = bus or event_bus
        self.security_provider = SecurityProvider(config=self.config)
        self.audit_logger = SecurityAuditLogger(repository=self.storage, config=self.config)

        # Domain Services
        self.user_manager = UserManager(repository=self.storage)
        self.profile_manager = ProfileManager(repository=self.storage)
        self.session_manager = SessionManager(repository=self.storage, config=self.config)
        self.preference_manager = PreferenceManager(repository=self.storage, config=self.config)
        self.auth_service = AuthenticationService(
            user_manager=self.user_manager,
            profile_manager=self.profile_manager,
            session_manager=self.session_manager,
            preference_manager=self.preference_manager,
            reset_repository=self.storage,
            audit_logger=self.audit_logger,
            security_provider=self.security_provider,
            config=self.config,
        )

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
        """Registers user and emits 'UserRegistered' event."""
        result = self.auth_service.register_user(
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
        if result.success and result.user_profile:
            self.event_bus.emit(
                "UserRegistered",
                user_id=result.user_profile.user_id,
                username=result.user_profile.username,
                email=result.user_profile.email,
            )
        return result

    def login(
        self,
        identifier: str,
        password: str,
        device_id: str = "default_device",
        device_name: str = "Desktop Client",
        ip_address: str = "127.0.0.1",
        remember_me: bool = False,
    ) -> AuthResult:
        """Authenticates user credentials and emits 'UserAuthenticated' event."""
        result = self.auth_service.login(
            identifier=identifier,
            password=password,
            device_id=device_id,
            device_name=device_name,
            ip_address=ip_address,
            remember_me=remember_me,
        )
        if result.success and result.user_profile:
            self.event_bus.emit(
                "UserAuthenticated",
                user_id=result.user_profile.user_id,
                username=result.user_profile.username,
                session_token=result.session_token,
                device_id=device_id,
            )
        return result

    def logout(self, session_token: str) -> bool:
        """Logs out user session and emits 'UserLoggedOut' event."""
        session = self.session_manager.validate_session_token(session_token)
        success = self.auth_service.logout(session_token)
        if success and session:
            self.event_bus.emit(
                "UserLoggedOut",
                user_id=session.user_id,
                session_id=session.session_id,
            )
        return success

    def validate_session(self, session_token: str) -> AuthResult:
        """Validates active session and returns context."""
        return self.auth_service.validate_session(session_token)

    def login_with_remember_token(
        self,
        remember_me_token: str,
        device_id: str = "default_device",
        ip_address: str = "127.0.0.1",
    ) -> AuthResult:
        """Logs in user via remember-me token."""
        result = self.auth_service.login_with_remember_token(
            remember_me_token=remember_me_token,
            device_id=device_id,
            ip_address=ip_address,
        )
        if result.success and result.user_profile:
            self.event_bus.emit(
                "UserAuthenticated",
                user_id=result.user_profile.user_id,
                username=result.user_profile.username,
                session_token=result.session_token,
                device_id=device_id,
                mechanism="remember_me",
            )
        return result

    def request_password_reset(self, identifier: str) -> Tuple[bool, str]:
        """Initiates password reset request."""
        success, reset_token = self.auth_service.request_password_reset(identifier)
        if success and not reset_token.startswith("If an account"):
            self.event_bus.emit("PasswordResetRequested", identifier=identifier)
        return success, reset_token

    def confirm_password_reset(self, reset_token: str, new_password: str) -> Tuple[bool, str]:
        """Confirms password reset request."""
        success, msg = self.auth_service.confirm_password_reset(reset_token, new_password)
        if success:
            self.event_bus.emit("PasswordResetConfirmed", status="success")
        return success, msg

    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Retrieves user profile."""
        return self.profile_manager.get_profile(user_id)

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
        """Updates user profile fields and emits 'UserProfileUpdated' event."""
        updated = self.profile_manager.update_profile(
            user_id=user_id,
            display_name=display_name,
            email=email,
            avatar=avatar,
            language_preference=language_preference,
            time_zone=time_zone,
            theme_preference=theme_preference,
        )
        self.event_bus.emit("UserProfileUpdated", user_id=user_id)
        return updated

    def get_preferences(self, user_id: str) -> UserPreferences:
        """Retrieves user preferences."""
        return self.preference_manager.get_preferences(user_id)

    def update_preferences(
        self,
        user_id: str,
        **kwargs,
    ) -> UserPreferences:
        """Updates user preferences and emits 'UserPreferencesChanged' event."""
        updated = self.preference_manager.update_preferences(user_id, **kwargs)
        self.event_bus.emit(
            "UserPreferencesChanged",
            user_id=user_id,
            wake_word=updated.wake_word,
            voice_id=updated.voice_settings.voice_id,
            assistant_name=updated.assistant_name,
            preferred_language=updated.preferred_language,
        )
        return updated

    def get_active_sessions(self, user_id: str) -> List[Session]:
        """Retrieves active sessions for a user."""
        return self.session_manager.get_user_active_sessions(user_id)

    def revoke_session(self, session_id: str) -> bool:
        """Revokes a session by ID."""
        success = self.session_manager.revoke_session(session_id)
        if success:
            self.event_bus.emit("SessionRevoked", session_id=session_id)
        return success

    def get_security_context(self, session_token: Optional[str] = None) -> SecurityContext:
        """Constructs SecurityContext from session token."""
        if not session_token:
            return SecurityContext(is_authenticated=False)
        session = self.session_manager.validate_session_token(session_token)
        if not session:
            return SecurityContext(is_authenticated=False)
        user = self.user_manager.get_user_by_id(session.user_id)
        return self.security_provider.build_security_context(session, user=user)
