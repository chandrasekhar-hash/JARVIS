"""
Data Models for J.A.R.V.I.S. Product Layer (Phase P1.1).
Strongly typed domain entities, data classes, enums, and serialization structures.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
import time


class AccountStatus(str, Enum):
    """Account operational status enum."""
    ACTIVE = "ACTIVE"
    LOCKED = "LOCKED"
    SUSPENDED = "SUSPENDED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"


class Role(str, Enum):
    """Role-based access control user role enum."""
    USER = "USER"
    ADMIN = "ADMIN"
    DEVELOPER = "DEVELOPER"


@dataclass
class User:
    """Core user security account entity."""
    user_id: str
    username: str
    email: str
    password_hash: str
    salt: str
    role: Role = Role.USER
    status: AccountStatus = AccountStatus.ACTIVE
    failed_login_attempts: int = 0
    locked_until: Optional[float] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def is_locked(self, current_time: Optional[float] = None) -> bool:
        """Returns True if the user account is currently locked."""
        if self.status == AccountStatus.LOCKED:
            now = current_time if current_time is not None else time.time()
            if self.locked_until and now < self.locked_until:
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Returns dictionary representation excluding sensitive credentials."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "role": self.role.value if isinstance(self.role, Role) else str(self.role),
            "status": self.status.value if isinstance(self.status, AccountStatus) else str(self.status),
            "failed_login_attempts": self.failed_login_attempts,
            "locked_until": self.locked_until,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class UserProfile:
    """User Profile metadata entity."""
    user_id: str
    username: str
    display_name: str
    email: str
    avatar: str = ""
    language_preference: str = "en-US"
    time_zone: str = "UTC"
    theme_preference: str = "dark"
    account_creation_date: float = field(default_factory=time.time)
    last_login: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializes user profile into a standard dictionary."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "display_name": self.display_name,
            "email": self.email,
            "avatar": self.avatar,
            "language_preference": self.language_preference,
            "time_zone": self.time_zone,
            "theme_preference": self.theme_preference,
            "account_creation_date": self.account_creation_date,
            "last_login": self.last_login,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserProfile":
        """Instantiates UserProfile from dictionary data."""
        return cls(
            user_id=data.get("user_id", ""),
            username=data.get("username", ""),
            display_name=data.get("display_name", ""),
            email=data.get("email", ""),
            avatar=data.get("avatar", ""),
            language_preference=data.get("language_preference", "en-US"),
            time_zone=data.get("time_zone", "UTC"),
            theme_preference=data.get("theme_preference", "dark"),
            account_creation_date=data.get("account_creation_date", time.time()),
            last_login=data.get("last_login"),
        )


@dataclass
class VoiceSettings:
    """User-specific voice synthesis settings."""
    voice_id: str = "en-US-Neural"
    speech_rate: float = 1.0
    speech_pitch: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "voice_id": self.voice_id,
            "speech_rate": self.speech_rate,
            "speech_pitch": self.speech_pitch,
        }


@dataclass
class NotificationSettings:
    """User notification preferences."""
    mute_audio: bool = False
    audio_chimes: bool = True
    os_popups: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mute_audio": self.mute_audio,
            "audio_chimes": self.audio_chimes,
            "os_popups": self.os_popups,
        }


@dataclass
class PrivacySettings:
    """User privacy and telemetry preferences."""
    cloud_telemetry: bool = False
    privacy_level: str = "standard"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cloud_telemetry": self.cloud_telemetry,
            "privacy_level": self.privacy_level,
        }


@dataclass
class UserPreferences:
    """Comprehensive user preferences entity."""
    user_id: str
    voice_settings: VoiceSettings = field(default_factory=VoiceSettings)
    wake_word: str = "JARVIS"
    assistant_name: str = "J.A.R.V.I.S."
    preferred_ai_model: str = "gemini-2.5-flash"
    preferred_language: str = "en-US"
    notification_settings: NotificationSettings = field(default_factory=NotificationSettings)
    privacy_settings: PrivacySettings = field(default_factory=PrivacySettings)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes user preferences into dictionary format."""
        return {
            "user_id": self.user_id,
            "voice_settings": self.voice_settings.to_dict(),
            "wake_word": self.wake_word,
            "assistant_name": self.assistant_name,
            "preferred_ai_model": self.preferred_ai_model,
            "preferred_language": self.preferred_language,
            "notification_settings": self.notification_settings.to_dict(),
            "privacy_settings": self.privacy_settings.to_dict(),
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserPreferences":
        """Instantiates UserPreferences from nested dictionary."""
        vs_data = data.get("voice_settings", {})
        voice_settings = VoiceSettings(
            voice_id=vs_data.get("voice_id", "en-US-Neural"),
            speech_rate=vs_data.get("speech_rate", 1.0),
            speech_pitch=vs_data.get("speech_pitch", 1.0),
        )
        ns_data = data.get("notification_settings", {})
        notification_settings = NotificationSettings(
            mute_audio=ns_data.get("mute_audio", False),
            audio_chimes=ns_data.get("audio_chimes", True),
            os_popups=ns_data.get("os_popups", True),
        )
        ps_data = data.get("privacy_settings", {})
        privacy_settings = PrivacySettings(
            cloud_telemetry=ps_data.get("cloud_telemetry", False),
            privacy_level=ps_data.get("privacy_level", "standard"),
        )
        return cls(
            user_id=data.get("user_id", ""),
            voice_settings=voice_settings,
            wake_word=data.get("wake_word", "JARVIS"),
            assistant_name=data.get("assistant_name", "J.A.R.V.I.S."),
            preferred_ai_model=data.get("preferred_ai_model", "gemini-2.5-flash"),
            preferred_language=data.get("preferred_language", "en-US"),
            notification_settings=notification_settings,
            privacy_settings=privacy_settings,
            updated_at=data.get("updated_at", time.time()),
        )


@dataclass
class Session:
    """Active user session tracking entity."""
    session_id: str
    user_id: str
    token: str
    device_id: str = "default_device"
    device_name: str = "Desktop Client"
    ip_address: str = "127.0.0.1"
    remember_me_token: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 86400)
    last_accessed_at: float = field(default_factory=time.time)
    is_active: bool = True

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        """Checks if session has expired."""
        now = current_time if current_time is not None else time.time()
        return not self.is_active or now >= self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Serializes session entity into dictionary format."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "device_id": self.device_id,
            "device_name": self.device_name,
            "ip_address": self.ip_address,
            "token": self.token,
            "remember_me_token": self.remember_me_token,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "last_accessed_at": self.last_accessed_at,
            "is_active": self.is_active,
        }


@dataclass
class PasswordResetToken:
    """Password reset request tracking record."""
    token_id: str
    user_id: str
    token_hash: str
    expires_at: float
    created_at: float = field(default_factory=time.time)
    used: bool = False

    def is_valid(self, current_time: Optional[float] = None) -> bool:
        """Validates if token is unused and not expired."""
        now = current_time if current_time is not None else time.time()
        return not self.used and now < self.expires_at


@dataclass
class AuthResult:
    """Standard authentication workflow output structure."""
    success: bool
    message: str
    user_profile: Optional[UserProfile] = None
    session_token: Optional[str] = None
    remember_me_token: Optional[str] = None
    session: Optional[Session] = None
    preferences: Optional[UserPreferences] = None
    error_code: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converts AuthResult to dictionary format."""
        return {
            "success": self.success,
            "message": self.message,
            "user_profile": self.user_profile.to_dict() if self.user_profile else None,
            "session_token": self.session_token,
            "remember_me_token": self.remember_me_token,
            "session": self.session.to_dict() if self.session else None,
            "preferences": self.preferences.to_dict() if self.preferences else None,
            "error_code": self.error_code,
        }


@dataclass
class SecurityContext:
    """Security context for authentication middleware and permission verification."""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    roles: List[str] = field(default_factory=lambda: [Role.USER.value])
    permissions: List[str] = field(default_factory=lambda: ["read", "execute"])
    is_authenticated: bool = False
    ip_address: str = "127.0.0.1"
    device_id: str = "unknown"

    def has_permission(self, required_permission: str) -> bool:
        """Returns True if the security context has the required permission."""
        return Role.ADMIN.value in self.roles or Role.DEVELOPER.value in self.roles or required_permission in self.permissions
