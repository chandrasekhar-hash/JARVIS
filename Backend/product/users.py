"""
User Account Manager Service for J.A.R.V.I.S. Product Layer (Phase P1.1).
Handles core account creation, user lookup, status transitions, roles, and failed attempt lockouts.
"""
import time
import logging
from typing import Optional, Tuple

from .models import User, AccountStatus, Role
from .interfaces import IUserRepository, ITokenGenerator
from .security import TokenGenerator

logger = logging.getLogger("JARVIS_UserManager")


class UserManager:
    """
    User Account Management domain service.
    Orchestrates user record creation, verification, status state machine, roles, and lockout logic.
    """

    def __init__(
        self,
        repository: IUserRepository,
        token_generator: Optional[ITokenGenerator] = None,
    ):
        self.repository = repository
        self.token_generator = token_generator or TokenGenerator()

    def create_user_account(
        self,
        username: str,
        email: str,
        password_hash: str,
        salt: str,
        role: Role = Role.USER,
        user_id: Optional[str] = None,
    ) -> User:
        """
        Creates and persists a new User account.
        Raises ValueError on conflict or invalid fields.
        """
        clean_username = username.strip()
        clean_email = email.strip()

        if self.repository.get_user_by_username(clean_username):
            raise ValueError(f"Username '{clean_username}' is already registered.")

        if self.repository.get_user_by_email(clean_email):
            raise ValueError(f"Email address '{clean_email}' is already registered.")

        uid = user_id or self.token_generator.generate_uuid(prefix="usr")
        now = time.time()
        user = User(
            user_id=uid,
            username=clean_username,
            email=clean_email,
            password_hash=password_hash,
            salt=salt,
            role=role,
            status=AccountStatus.ACTIVE,
            failed_login_attempts=0,
            locked_until=None,
            created_at=now,
            updated_at=now,
        )
        return self.repository.create_user(user)

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Retrieves user by user ID."""
        return self.repository.get_user_by_id(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Retrieves user by username."""
        return self.repository.get_user_by_username(username)

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Retrieves user by email."""
        return self.repository.get_user_by_email(email)

    def find_by_identifier(self, identifier: str) -> Optional[User]:
        """Finds user by either username or email address."""
        if not identifier:
            return None
        clean_id = identifier.strip()
        user = self.get_user_by_username(clean_id)
        if not user:
            user = self.get_user_by_email(clean_id)
        return user

    def record_failed_login(
        self, user_id: str, max_attempts: int = 5, lockout_seconds: int = 900
    ) -> User:
        """
        Increments failed login attempts and locks account if threshold exceeded.
        """
        user = self.repository.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User '{user_id}' not found.")

        user.failed_login_attempts += 1
        now = time.time()
        if user.failed_login_attempts >= max_attempts:
            user.status = AccountStatus.LOCKED
            user.locked_until = now + lockout_seconds
            logger.warning(
                f"[UserManager] User '{user.username}' locked out for {lockout_seconds}s after {user.failed_login_attempts} failed attempts."
            )

        return self.repository.update_user(user)

    def record_successful_login(self, user_id: str) -> User:
        """Resets failed login attempt counter and unlocks account if lockout period expired."""
        user = self.repository.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User '{user_id}' not found.")

        user.failed_login_attempts = 0
        user.locked_until = None
        if user.status == AccountStatus.LOCKED:
            user.status = AccountStatus.ACTIVE
        return self.repository.update_user(user)

    def update_password(self, user_id: str, new_password_hash: str, new_salt: str) -> User:
        """Updates user credentials password hash and salt."""
        user = self.repository.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User '{user_id}' not found.")

        user.password_hash = new_password_hash
        user.salt = new_salt
        user.failed_login_attempts = 0
        user.locked_until = None
        if user.status == AccountStatus.LOCKED:
            user.status = AccountStatus.ACTIVE
        return self.repository.update_user(user)

    def delete_user_account(self, user_id: str) -> bool:
        """Deletes user account record."""
        return self.repository.delete_user(user_id)
