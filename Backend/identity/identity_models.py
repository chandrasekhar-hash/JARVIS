from enum import Enum
from typing import List, Dict, Any, Optional
import time
from pydantic import BaseModel, Field


class DeviceTrustState(str, Enum):
    UNTRUSTED = "untrusted"
    PROVISIONAL = "provisional"
    TRUSTED = "trusted"
    REVOKED = "revoked"


class AuthProviderEnum(str, Enum):
    LOCAL = "local"
    OAUTH = "oauth"
    GOOGLE = "google"
    GITHUB = "github"
    APPLE = "apple"
    MICROSOFT = "microsoft"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class UserProfile(BaseModel):
    user_id: str
    display_name: str = "J.A.R.V.I.S. User"
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    locale: str = "en-US"
    timezone: str = "UTC"
    theme: str = "dark"
    ai_defaults: Dict[str, Any] = Field(default_factory=lambda: {
        "preferred_provider": "groq",
        "default_model": "llama-3.3-70b",
        "voice_synthesis_engine": "edge",
        "voice_name": "female"
    })


class DeviceProfile(BaseModel):
    device_id: str
    device_name: str
    platform: str
    architecture: str
    os_version: str
    app_version: str = "1.0.0"
    installation_date: float = Field(default_factory=time.time)
    public_key: str
    public_key_fingerprint: str
    trust_state: DeviceTrustState = DeviceTrustState.TRUSTED
    updated_at: float = Field(default_factory=time.time)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 86400  # 24 hours in seconds


class SessionToken(BaseModel):
    session_id: str
    user_id: str
    device_id: str
    access_token: str
    refresh_token: str
    expires_at: float
    refresh_expires_at: float
    created_at: float = Field(default_factory=time.time)
    status: SessionStatus = SessionStatus.ACTIVE
    ip_address: str = "127.0.0.1"
    user_agent: str = "JARVIS Local Agent"


class SecurityStatus(BaseModel):
    zero_trust_enabled: bool = True
    local_first_mode: bool = True
    active_sessions_count: int = 0
    active_devices_count: int = 1
    device_key_fingerprint: str = ""
    current_schema_version: str = "v1_identity_security"
    crypto_algorithm: str = "Ed25519"
