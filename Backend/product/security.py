"""
Security Primitives, Cryptographic Hasher, Input Validator, Rate Limiter, and Middleware
for J.A.R.V.I.S. Product Layer (Phase P1.1).
"""
import re
import time
import secrets
import uuid
import hashlib
from typing import Tuple, Optional, Dict, List
import logging

from .config import ProductConfig, product_config
from .models import Session, SecurityContext, User, Role
from .interfaces import IPasswordHasher, ITokenGenerator, ISecurityProvider

logger = logging.getLogger("JARVIS_ProductSecurity")


class PasswordHasher(IPasswordHasher):
    """
    PBKDF2-HMAC-SHA256 password hasher with salt generation and constant-time verification.
    """

    def __init__(self, config: Optional[ProductConfig] = None):
        self.config = config or product_config

    def hash_password(self, password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """
        Hashes password using PBKDF2-HMAC-SHA256.
        Returns: (hash_hex, salt_hex)
        """
        if not password:
            raise ValueError("Password cannot be empty.")

        if salt is None:
            salt_bytes = secrets.token_bytes(self.config.salt_length_bytes)
        else:
            salt_bytes = bytes.fromhex(salt)

        derived = hashlib.pbkdf2_hmac(
            hash_name=self.config.hash_algorithm,
            password=password.encode("utf-8"),
            salt=salt_bytes,
            iterations=self.config.hash_iterations,
        )
        return derived.hex(), salt_bytes.hex()

    def verify_password(self, password: str, stored_hash: str, stored_salt: str) -> bool:
        """
        Verifies candidate password against stored hash and salt using constant-time comparison.
        """
        if not password or not stored_hash or not stored_salt:
            return False

        try:
            salt_bytes = bytes.fromhex(stored_salt)
            computed_hash_hex, _ = self.hash_password(password, salt=stored_salt)
            return secrets.compare_digest(computed_hash_hex, stored_hash)
        except Exception as e:
            logger.error(f"[PasswordHasher] Error verifying password: {e}")
            return False


class TokenGenerator(ITokenGenerator):
    """
    Cryptographically secure random token and UUID generator.
    """

    def __init__(self, config: Optional[ProductConfig] = None):
        self.config = config or product_config

    def generate_token(self, prefix: str = "") -> str:
        """Generates a URL-safe cryptographically secure random token string."""
        raw_token = secrets.token_urlsafe(self.config.token_entropy_bytes)
        return f"{prefix}_{raw_token}" if prefix else raw_token

    def generate_uuid(self, prefix: str = "") -> str:
        """Generates a UUID4 identifier with optional prefix."""
        uid_str = str(uuid.uuid4())
        return f"{prefix}_{uid_str}" if prefix else uid_str


class InputValidator:
    """
    Input validation utility for sanitizing and checking user fields against security policies.
    """

    EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_-]{3,30}$")

    def __init__(self, config: Optional[ProductConfig] = None):
        self.config = config or product_config

    def validate_email(self, email: str) -> Tuple[bool, str]:
        """Validates email format."""
        if not email or not isinstance(email, str):
            return False, "Email address is required."

        clean_email = email.strip()
        if not self.EMAIL_REGEX.match(clean_email):
            return False, "Invalid email address format."

        return True, "Valid email."

    def validate_username(self, username: str) -> Tuple[bool, str]:
        """Validates username constraints."""
        if not username or not isinstance(username, str):
            return False, "Username is required."

        clean_username = username.strip()
        if len(clean_username) < 3 or len(clean_username) > 30:
            return False, "Username must be between 3 and 30 characters long."

        if not self.USERNAME_REGEX.match(clean_username):
            return False, "Username can only contain letters, numbers, underscores, and hyphens."

        return True, "Valid username."

    def validate_password(self, password: str) -> Tuple[bool, str]:
        """Validates password against complexity requirements."""
        if not password or not isinstance(password, str):
            return False, "Password is required."

        if len(password) < self.config.min_password_length:
            return False, f"Password must be at least {self.config.min_password_length} characters long."

        if self.config.require_uppercase and not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter."

        if self.config.require_lowercase and not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter."

        if self.config.require_digits and not any(c.isdigit() for c in password):
            return False, "Password must contain at least one digit."

        if self.config.require_special_char and not any(not c.isalnum() for c in password):
            return False, "Password must contain at least one special character."

        return True, "Valid password."


class SlidingWindowRateLimiter:
    """
    In-memory sliding window rate limiter for security endpoints.
    """

    def __init__(self, max_attempts: int = 10, window_seconds: int = 60):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._records: Dict[str, List[float]] = {}

    def is_allowed(self, identifier: str) -> Tuple[bool, str]:
        """
        Checks if the identifier is within rate limits.
        Returns: (allowed, message)
        """
        now = time.time()
        window_start = now - self.window_seconds

        if identifier not in self._records:
            self._records[identifier] = []

        self._records[identifier] = [
            ts for ts in self._records[identifier] if ts > window_start
        ]

        if len(self._records[identifier]) >= self.max_attempts:
            return False, f"Rate limit exceeded. Maximum {self.max_attempts} requests per {self.window_seconds} seconds."

        self._records[identifier].append(now)
        return True, "Allowed."

    def reset(self, identifier: str) -> None:
        """Resets rate limit counter for a specific identifier."""
        if identifier in self._records:
            del self._records[identifier]


class SecurityProvider(ISecurityProvider):
    """
    Comprehensive Security Provider orchestrating hashing, validation, rate limiting, and security context creation.
    """

    def __init__(self, config: Optional[ProductConfig] = None):
        self.config = config or product_config
        self.hasher = PasswordHasher(self.config)
        self.token_gen = TokenGenerator(self.config)
        self.validator = InputValidator(self.config)
        self.rate_limiter = SlidingWindowRateLimiter(
            max_attempts=self.config.rate_limit_max_attempts,
            window_seconds=self.config.rate_limit_window_seconds,
        )

    def validate_email(self, email: str) -> Tuple[bool, str]:
        return self.validator.validate_email(email)

    def validate_username(self, username: str) -> Tuple[bool, str]:
        return self.validator.validate_username(username)

    def validate_password(self, password: str) -> Tuple[bool, str]:
        return self.validator.validate_password(password)

    def check_rate_limit(self, identifier: str) -> Tuple[bool, str]:
        return self.rate_limiter.is_allowed(identifier)

    def build_security_context(
        self,
        session: Optional[Session],
        user: Optional[User] = None,
        role: Optional[Role] = None,
    ) -> SecurityContext:
        """Constructs SecurityContext from active session and role."""
        if session and session.is_active and not session.is_expired():
            role_val = role.value if role else (user.role.value if user else Role.USER.value)
            return SecurityContext(
                user_id=session.user_id,
                session_id=session.session_id,
                roles=[role_val],
                permissions=["read", "write", "execute"],
                is_authenticated=True,
                ip_address=session.ip_address,
                device_id=session.device_id,
            )
        return SecurityContext(is_authenticated=False)


# Default singleton instance
security_provider = SecurityProvider()
