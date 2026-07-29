"""
Abstract Base Classes & Interfaces for J.A.R.V.I.S. Product Layer (Phase P1.1).
Adheres strictly to SOLID principles and Dependency Injection standards.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple, Dict, Any
from .models import (
    User,
    UserProfile,
    Session,
    UserPreferences,
    PasswordResetToken,
    SecurityContext,
)


class IUserRepository(ABC):
    """Abstract Repository Interface for User entity persistence."""

    @abstractmethod
    def create_user(self, user: User) -> User:
        """Persists a new User record."""
        pass

    @abstractmethod
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Retrieves a User by unique user ID."""
        pass

    @abstractmethod
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Retrieves a User by username."""
        pass

    @abstractmethod
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Retrieves a User by email address."""
        pass

    @abstractmethod
    def update_user(self, user: User) -> User:
        """Updates an existing User record."""
        pass

    @abstractmethod
    def delete_user(self, user_id: str) -> bool:
        """Deletes a User record by user ID."""
        pass


class IProfileRepository(ABC):
    """Abstract Repository Interface for UserProfile persistence."""

    @abstractmethod
    def create_profile(self, profile: UserProfile) -> UserProfile:
        """Persists a new UserProfile record."""
        pass

    @abstractmethod
    def get_profile_by_user_id(self, user_id: str) -> Optional[UserProfile]:
        """Retrieves UserProfile by user ID."""
        pass

    @abstractmethod
    def update_profile(self, profile: UserProfile) -> UserProfile:
        """Updates an existing UserProfile."""
        pass

    @abstractmethod
    def delete_profile(self, user_id: str) -> bool:
        """Deletes a UserProfile record."""
        pass


class ISessionRepository(ABC):
    """Abstract Repository Interface for Session tracking persistence."""

    @abstractmethod
    def create_session(self, session: Session) -> Session:
        """Persists a new active session."""
        pass

    @abstractmethod
    def get_session_by_token(self, token: str) -> Optional[Session]:
        """Retrieves a Session by active token."""
        pass

    @abstractmethod
    def get_session_by_id(self, session_id: str) -> Optional[Session]:
        """Retrieves a Session by session ID."""
        pass

    @abstractmethod
    def get_session_by_remember_token(self, remember_me_token: str) -> Optional[Session]:
        """Retrieves a Session by remember-me token."""
        pass

    @abstractmethod
    def get_user_sessions(self, user_id: str) -> List[Session]:
        """Retrieves all sessions belonging to a specific user ID."""
        pass

    @abstractmethod
    def update_session(self, session: Session) -> Session:
        """Updates an existing session."""
        pass

    @abstractmethod
    def revoke_session(self, session_id: str) -> bool:
        """Revokes a specific session by ID."""
        pass

    @abstractmethod
    def revoke_all_user_sessions(self, user_id: str) -> int:
        """Revokes all sessions belonging to a user ID."""
        pass


class IPreferenceRepository(ABC):
    """Abstract Repository Interface for UserPreferences persistence."""

    @abstractmethod
    def create_preferences(self, preferences: UserPreferences) -> UserPreferences:
        """Persists initial UserPreferences for a user."""
        pass

    @abstractmethod
    def get_preferences_by_user_id(self, user_id: str) -> Optional[UserPreferences]:
        """Retrieves UserPreferences by user ID."""
        pass

    @abstractmethod
    def update_preferences(self, preferences: UserPreferences) -> UserPreferences:
        """Updates UserPreferences."""
        pass

    @abstractmethod
    def delete_preferences(self, user_id: str) -> bool:
        """Deletes UserPreferences record."""
        pass


class IPasswordResetRepository(ABC):
    """Abstract Repository Interface for PasswordResetToken persistence."""

    @abstractmethod
    def create_reset_token(self, token: PasswordResetToken) -> PasswordResetToken:
        """Persists a new password reset token."""
        pass

    @abstractmethod
    def get_reset_token(self, token_hash: str) -> Optional[PasswordResetToken]:
        """Retrieves a password reset token by hash."""
        pass

    @abstractmethod
    def mark_reset_token_used(self, token_id: str) -> bool:
        """Marks a password reset token as consumed/used."""
        pass


class IAuditRepository(ABC):
    """Abstract Repository Interface for append-only Security Audit Logging."""

    @abstractmethod
    def log_audit_entry(self, entry: Any) -> Any:
        """Appends a new security audit log entry."""
        pass

    @abstractmethod
    def query_audit_logs(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Any]:
        """Queries security audit log entries with optional filtering."""
        pass


class IPasswordHasher(ABC):
    """Abstract Interface for password hashing & verification algorithms."""

    @abstractmethod
    def hash_password(self, password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """Hashes password string with salt. Returns (hash_hex, salt_hex)."""
        pass

    @abstractmethod
    def verify_password(self, password: str, stored_hash: str, stored_salt: str) -> bool:
        """Verifies candidate password against stored hash and salt."""
        pass


class ITokenGenerator(ABC):
    """Abstract Interface for cryptographically secure token generation."""

    @abstractmethod
    def generate_token(self, prefix: str = "") -> str:
        """Generates a secure random token."""
        pass

    @abstractmethod
    def generate_uuid(self, prefix: str = "") -> str:
        """Generates a unique UUID4 identifier."""
        pass


class ISecurityProvider(ABC):
    """Abstract Interface for security checks, validation, and middleware context."""

    @abstractmethod
    def validate_email(self, email: str) -> Tuple[bool, str]:
        """Validates email format."""
        pass

    @abstractmethod
    def validate_username(self, username: str) -> Tuple[bool, str]:
        """Validates username format and constraints."""
        pass

    @abstractmethod
    def validate_password(self, password: str) -> Tuple[bool, str]:
        """Validates password strength requirements."""
        pass

    @abstractmethod
    def check_rate_limit(self, identifier: str) -> Tuple[bool, str]:
        """Checks sliding window rate limit for an identifier."""
        pass

    @abstractmethod
    def build_security_context(self, session: Optional[Session], role: Optional[str] = None) -> SecurityContext:
        """Constructs SecurityContext from an active session."""
        pass
