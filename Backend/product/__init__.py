"""
J.A.R.V.I.S. Product Layer (Phase P1.1) Package Initialization.
Exports Identity & User Management domain models, roles, security audit logging, interfaces, services, and public engine APIs.
"""
from .config import ProductConfig, product_config
from .models import (
    User,
    Role,
    AccountStatus,
    UserProfile,
    UserPreferences,
    VoiceSettings,
    NotificationSettings,
    PrivacySettings,
    Session,
    PasswordResetToken,
    AuthResult,
    SecurityContext,
)
from .interfaces import (
    IUserRepository,
    IProfileRepository,
    ISessionRepository,
    IPreferenceRepository,
    IPasswordResetRepository,
    IAuditRepository,
    IPasswordHasher,
    ITokenGenerator,
    ISecurityProvider,
)
from .security import (
    PasswordHasher,
    TokenGenerator,
    InputValidator,
    SlidingWindowRateLimiter,
    SecurityProvider,
    security_provider,
)
from .audit import (
    AuditLevel,
    AuditEvent,
    AuditEntry,
    SecurityAuditLogger,
)
from .storage import SQLiteProductStorage
from .users import UserManager
from .profiles import ProfileManager
from .sessions import SessionManager
from .preferences import PreferenceManager
from .authentication import AuthenticationService
from .coordinator import ProductCoordinator
from .engine import ProductEngine, product_engine

__all__ = [
    "ProductConfig",
    "product_config",
    "User",
    "Role",
    "AccountStatus",
    "UserProfile",
    "UserPreferences",
    "VoiceSettings",
    "NotificationSettings",
    "PrivacySettings",
    "Session",
    "PasswordResetToken",
    "AuthResult",
    "SecurityContext",
    "IUserRepository",
    "IProfileRepository",
    "ISessionRepository",
    "IPreferenceRepository",
    "IPasswordResetRepository",
    "IAuditRepository",
    "IPasswordHasher",
    "ITokenGenerator",
    "ISecurityProvider",
    "PasswordHasher",
    "TokenGenerator",
    "InputValidator",
    "SlidingWindowRateLimiter",
    "SecurityProvider",
    "security_provider",
    "AuditLevel",
    "AuditEvent",
    "AuditEntry",
    "SecurityAuditLogger",
    "SQLiteProductStorage",
    "UserManager",
    "ProfileManager",
    "SessionManager",
    "PreferenceManager",
    "AuthenticationService",
    "ProductCoordinator",
    "ProductEngine",
    "product_engine",
]
