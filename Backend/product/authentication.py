"""
Authentication Service for J.A.R.V.I.S. Product Layer (Phase P1.1).
Handles registration, secure login, logout, password hashing/verification, password reset workflows, and remember-me support.
Logs audit-critical security events to SecurityAuditLogger.
"""
import time
import hashlib
import logging
from typing import Optional, Tuple

from .config import ProductConfig, product_config
from .models import (
    User,
    Role,
    UserProfile,
    Session,
    UserPreferences,
    PasswordResetToken,
    AuthResult,
    AccountStatus,
)
from .users import UserManager
from .profiles import ProfileManager
from .sessions import SessionManager
from .preferences import PreferenceManager
from .interfaces import ISecurityProvider, IPasswordResetRepository
from .security import SecurityProvider
from .audit import SecurityAuditLogger, AuditEvent, AuditLevel

logger = logging.getLogger("JARVIS_AuthenticationService")


class AuthenticationService:
    """
    Core Authentication Service orchestrating account registration, credential verification,
    session lifecycle, password reset tokens, security policies, and audit logging.
    """

    def __init__(
        self,
        user_manager: UserManager,
        profile_manager: ProfileManager,
        session_manager: SessionManager,
        preference_manager: PreferenceManager,
        reset_repository: IPasswordResetRepository,
        audit_logger: Optional[SecurityAuditLogger] = None,
        security_provider: Optional[ISecurityProvider] = None,
        config: Optional[ProductConfig] = None,
    ):
        self.user_manager = user_manager
        self.profile_manager = profile_manager
        self.session_manager = session_manager
        self.preference_manager = preference_manager
        self.reset_repository = reset_repository
        self.audit_logger = audit_logger
        self.security_provider = security_provider or SecurityProvider()
        self.config = config or product_config

    def _audit(
        self,
        event_type: AuditEvent,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        severity: AuditLevel = AuditLevel.INFO,
        device_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        result: str = "SUCCESS",
        metadata: Optional[dict] = None,
    ) -> None:
        """Helper to safely record security audit log entries."""
        if self.audit_logger:
            try:
                self.audit_logger.record_event(
                    event_type=event_type,
                    user_id=user_id,
                    session_id=session_id,
                    severity=severity,
                    device_id=device_id,
                    ip_address=ip_address,
                    result=result,
                    metadata=metadata,
                )
            except Exception as e:
                logger.error(f"[AuthenticationService] Audit logging failed: {e}")

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
        """
        Registers a new user account, creates initial profile and default user preferences.
        """
        # Validate Input
        valid, msg = self.security_provider.validate_username(username)
        if not valid:
            self._audit(AuditEvent.USER_REGISTERED, result="FAILURE", metadata={"reason": msg})
            return AuthResult(success=False, message=msg, error_code="INVALID_USERNAME")

        valid, msg = self.security_provider.validate_email(email)
        if not valid:
            self._audit(AuditEvent.USER_REGISTERED, result="FAILURE", metadata={"reason": msg})
            return AuthResult(success=False, message=msg, error_code="INVALID_EMAIL")

        valid, msg = self.security_provider.validate_password(password)
        if not valid:
            self._audit(AuditEvent.USER_REGISTERED, result="FAILURE", metadata={"reason": msg})
            return AuthResult(success=False, message=msg, error_code="INVALID_PASSWORD")

        # Check existing user/email conflicts
        if self.user_manager.get_user_by_username(username):
            self._audit(AuditEvent.USER_REGISTERED, result="FAILURE", metadata={"reason": "Username exists"})
            return AuthResult(success=False, message="Username is already in use.", error_code="USERNAME_EXISTS")

        if self.user_manager.get_user_by_email(email):
            self._audit(AuditEvent.USER_REGISTERED, result="FAILURE", metadata={"reason": "Email exists"})
            return AuthResult(success=False, message="Email address is already in use.", error_code="EMAIL_EXISTS")

        try:
            # Hash password
            password_hash, salt = self.security_provider.hasher.hash_password(password)

            # Create User Account
            user = self.user_manager.create_user_account(
                username=username,
                email=email,
                password_hash=password_hash,
                salt=salt,
                role=role,
            )

            # Create User Profile
            profile = self.profile_manager.create_profile(
                user_id=user.user_id,
                username=user.username,
                display_name=display_name or user.username,
                email=user.email,
                avatar=avatar,
                language_preference=language_preference,
                time_zone=time_zone,
                theme_preference=theme_preference,
            )

            # Create Default Preferences
            preferences = self.preference_manager.create_default_preferences(user.user_id)

            self._audit(
                AuditEvent.USER_REGISTERED,
                user_id=user.user_id,
                severity=AuditLevel.INFO,
                result="SUCCESS",
                metadata={"username": username, "role": user.role.value},
            )

            logger.info(f"[AuthenticationService] Successfully registered user '{user.username}' (ID: {user.user_id}).")
            return AuthResult(
                success=True,
                message="User registered successfully.",
                user_profile=profile,
                preferences=preferences,
            )
        except Exception as e:
            logger.error(f"[AuthenticationService] Registration error for '{username}': {e}")
            self._audit(AuditEvent.USER_REGISTERED, result="FAILURE", metadata={"error": str(e)})
            return AuthResult(success=False, message=f"Registration failed: {str(e)}", error_code="REGISTRATION_FAILED")

    def login(
        self,
        identifier: str,
        password: str,
        device_id: str = "default_device",
        device_name: str = "Desktop Client",
        ip_address: str = "127.0.0.1",
        remember_me: bool = False,
    ) -> AuthResult:
        """
        Authenticates user with username/email and password credentials.
        Creates an active session and returns session tokens.
        """
        allowed, rate_msg = self.security_provider.check_rate_limit(identifier)
        if not allowed:
            self._audit(
                AuditEvent.LOGIN_FAILED,
                severity=AuditLevel.WARNING,
                device_id=device_id,
                ip_address=ip_address,
                result="FAILURE",
                metadata={"reason": "Rate limit exceeded"},
            )
            return AuthResult(success=False, message=rate_msg, error_code="RATE_LIMIT_EXCEEDED")

        user = self.user_manager.find_by_identifier(identifier)
        if not user:
            self._audit(
                AuditEvent.LOGIN_FAILED,
                severity=AuditLevel.WARNING,
                device_id=device_id,
                ip_address=ip_address,
                result="FAILURE",
                metadata={"identifier": identifier, "reason": "User not found"},
            )
            return AuthResult(success=False, message="Invalid username or password.", error_code="INVALID_CREDENTIALS")

        now = time.time()
        if user.is_locked(current_time=now):
            remaining = int(user.locked_until - now) if user.locked_until else 0
            self._audit(
                AuditEvent.LOGIN_FAILED,
                user_id=user.user_id,
                severity=AuditLevel.WARNING,
                device_id=device_id,
                ip_address=ip_address,
                result="FAILURE",
                metadata={"reason": "Account locked"},
            )
            return AuthResult(
                success=False,
                message=f"Account is temporarily locked due to failed login attempts. Try again in {remaining} seconds.",
                error_code="ACCOUNT_LOCKED",
            )

        if user.status == AccountStatus.SUSPENDED:
            self._audit(
                AuditEvent.LOGIN_FAILED,
                user_id=user.user_id,
                severity=AuditLevel.WARNING,
                device_id=device_id,
                ip_address=ip_address,
                result="FAILURE",
                metadata={"reason": "Account suspended"},
            )
            return AuthResult(success=False, message="Account has been suspended.", error_code="ACCOUNT_SUSPENDED")

        # Verify Password
        valid_password = self.security_provider.hasher.verify_password(
            password=password,
            stored_hash=user.password_hash,
            stored_salt=user.salt,
        )

        if not valid_password:
            updated_user = self.user_manager.record_failed_login(
                user_id=user.user_id,
                max_attempts=self.config.max_failed_login_attempts,
                lockout_seconds=self.config.account_lockout_seconds,
            )
            if updated_user.status == AccountStatus.LOCKED:
                self._audit(
                    AuditEvent.ACCOUNT_LOCKED,
                    user_id=user.user_id,
                    severity=AuditLevel.CRITICAL,
                    device_id=device_id,
                    ip_address=ip_address,
                    result="SUCCESS",
                    metadata={"failed_attempts": updated_user.failed_login_attempts},
                )
            else:
                self._audit(
                    AuditEvent.LOGIN_FAILED,
                    user_id=user.user_id,
                    severity=AuditLevel.WARNING,
                    device_id=device_id,
                    ip_address=ip_address,
                    result="FAILURE",
                    metadata={"reason": "Invalid password"},
                )
            return AuthResult(success=False, message="Invalid username or password.", error_code="INVALID_CREDENTIALS")

        # Reset failed login counter & update last login
        self.user_manager.record_successful_login(user.user_id)
        profile = self.profile_manager.record_login_timestamp(user.user_id, timestamp=now)
        if not profile:
            profile = self.profile_manager.get_profile(user.user_id)

        # Create active session
        session = self.session_manager.create_session(
            user_id=user.user_id,
            device_id=device_id,
            device_name=device_name,
            ip_address=ip_address,
            remember_me=remember_me,
        )

        preferences = self.preference_manager.get_preferences(user.user_id)

        self._audit(
            AuditEvent.LOGIN_SUCCESS,
            user_id=user.user_id,
            session_id=session.session_id,
            severity=AuditLevel.INFO,
            device_id=device_id,
            ip_address=ip_address,
            result="SUCCESS",
        )

        logger.info(f"[AuthenticationService] User '{user.username}' logged in successfully.")
        return AuthResult(
            success=True,
            message="Login successful.",
            user_profile=profile,
            session_token=session.token,
            remember_me_token=session.remember_me_token,
            session=session,
            preferences=preferences,
        )

    def logout(self, session_token: str) -> bool:
        """Logs out user by revoking the active session token."""
        if not session_token:
            return False
        session = self.session_manager.validate_session_token(session_token)
        success = self.session_manager.revoke_session_by_token(session_token)
        if success and session:
            self._audit(
                AuditEvent.LOGOUT,
                user_id=session.user_id,
                session_id=session.session_id,
                device_id=session.device_id,
                ip_address=session.ip_address,
                result="SUCCESS",
            )
        return success

    def validate_session(self, session_token: str) -> AuthResult:
        """Validates active session token and returns active user context."""
        session = self.session_manager.validate_session_token(session_token)
        if not session:
            return AuthResult(success=False, message="Session token is invalid or expired.", error_code="INVALID_SESSION")

        profile = self.profile_manager.get_profile(session.user_id)
        preferences = self.preference_manager.get_preferences(session.user_id)

        return AuthResult(
            success=True,
            message="Session is valid.",
            user_profile=profile,
            session_token=session.token,
            session=session,
            preferences=preferences,
        )

    def login_with_remember_token(
        self,
        remember_me_token: str,
        device_id: str = "default_device",
        ip_address: str = "127.0.0.1",
    ) -> AuthResult:
        """Logs in user automatically using a valid remember-me token."""
        session = self.session_manager.validate_remember_token(remember_me_token)
        if not session:
            self._audit(
                AuditEvent.LOGIN_FAILED,
                severity=AuditLevel.WARNING,
                device_id=device_id,
                ip_address=ip_address,
                result="FAILURE",
                metadata={"reason": "Invalid remember token"},
            )
            return AuthResult(success=False, message="Remember-me token is invalid or expired.", error_code="INVALID_REMEMBER_TOKEN")

        user = self.user_manager.get_user_by_id(session.user_id)
        if not user or user.status != AccountStatus.ACTIVE:
            return AuthResult(success=False, message="Account is inactive or suspended.", error_code="INACTIVE_ACCOUNT")

        new_session = self.session_manager.create_session(
            user_id=user.user_id,
            device_id=device_id,
            device_name=session.device_name,
            ip_address=ip_address,
            remember_me=True,
        )

        profile = self.profile_manager.record_login_timestamp(user.user_id)
        preferences = self.preference_manager.get_preferences(user.user_id)

        self._audit(
            AuditEvent.LOGIN_SUCCESS,
            user_id=user.user_id,
            session_id=new_session.session_id,
            severity=AuditLevel.INFO,
            device_id=device_id,
            ip_address=ip_address,
            result="SUCCESS",
            metadata={"mechanism": "remember_me"},
        )

        return AuthResult(
            success=True,
            message="Auto-login successful via remember-me token.",
            user_profile=profile,
            session_token=new_session.token,
            remember_me_token=new_session.remember_me_token,
            session=new_session,
            preferences=preferences,
        )

    def request_password_reset(self, identifier: str) -> Tuple[bool, str]:
        """
        Generates a time-bound password reset token for user account.
        """
        user = self.user_manager.find_by_identifier(identifier)
        if not user:
            return True, "If an account exists for this identifier, a password reset token has been generated."

        raw_reset_token = self.security_provider.token_gen.generate_token(prefix="rst")
        token_hash = hashlib.sha256(raw_reset_token.encode("utf-8")).hexdigest()
        expires_at = time.time() + self.config.reset_token_ttl_seconds
        token_id = self.security_provider.token_gen.generate_uuid(prefix="rst_id")

        reset_record = PasswordResetToken(
            token_id=token_id,
            user_id=user.user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            created_at=time.time(),
            used=False,
        )
        self.reset_repository.create_reset_token(reset_record)

        self._audit(
            AuditEvent.PASSWORD_RESET_REQUESTED,
            user_id=user.user_id,
            severity=AuditLevel.INFO,
            result="SUCCESS",
        )

        logger.info(f"[AuthenticationService] Password reset token generated for user '{user.username}'.")
        return True, raw_reset_token

    def confirm_password_reset(self, reset_token: str, new_password: str) -> Tuple[bool, str]:
        """Validates reset token and sets new account password."""
        if not reset_token:
            return False, "Reset token is required."

        valid, msg = self.security_provider.validate_password(new_password)
        if not valid:
            return False, msg

        token_hash = hashlib.sha256(reset_token.strip().encode("utf-8")).hexdigest()
        reset_record = self.reset_repository.get_reset_token(token_hash)

        if not reset_record or not reset_record.is_valid():
            return False, "Password reset token is invalid or has expired."

        new_hash, new_salt = self.security_provider.hasher.hash_password(new_password)

        self.user_manager.update_password(
            user_id=reset_record.user_id,
            new_password_hash=new_hash,
            new_salt=new_salt,
        )

        self.reset_repository.mark_reset_token_used(reset_record.token_id)
        self.session_manager.revoke_all_user_sessions(reset_record.user_id)

        self._audit(
            AuditEvent.PASSWORD_RESET_COMPLETED,
            user_id=reset_record.user_id,
            severity=AuditLevel.INFO,
            result="SUCCESS",
        )

        logger.info(f"[AuthenticationService] Password successfully reset for user_id '{reset_record.user_id}'.")
        return True, "Password reset successfully."

    def change_password(self, user_id: str, current_password: str, new_password: str) -> Tuple[bool, str]:
        """Allows logged-in user to change their account password."""
        user = self.user_manager.get_user_by_id(user_id)
        if not user:
            return False, "User not found."

        if not self.security_provider.hasher.verify_password(current_password, user.password_hash, user.salt):
            self._audit(
                AuditEvent.PASSWORD_CHANGED,
                user_id=user_id,
                severity=AuditLevel.WARNING,
                result="FAILURE",
                metadata={"reason": "Incorrect current password"},
            )
            return False, "Incorrect current password."

        valid, msg = self.security_provider.validate_password(new_password)
        if not valid:
            return False, msg

        new_hash, new_salt = self.security_provider.hasher.hash_password(new_password)
        self.user_manager.update_password(user_id, new_hash, new_salt)

        self._audit(
            AuditEvent.PASSWORD_CHANGED,
            user_id=user_id,
            severity=AuditLevel.INFO,
            result="SUCCESS",
        )
        return True, "Password changed successfully."
