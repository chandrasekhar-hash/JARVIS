from enum import Enum
from typing import List, Dict, Any, Optional
import time
from pydantic import BaseModel, Field


class DeviceTrustState(str, Enum):
    UNTRUSTED = "untrusted"
    PROVISIONAL = "provisional"
    TRUSTED = "trusted"
    REVOKED = "revoked"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class CloudUser(BaseModel):
    user_id: str
    display_name: str = "JARVIS Cloud User"
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    preferences: Dict[str, Any] = Field(default_factory=dict)


class CloudDevice(BaseModel):
    device_id: str
    user_id: str
    device_name: str
    platform: str
    architecture: str
    os_version: str
    app_version: str = "1.0.0"
    public_key: str
    public_key_fingerprint: str
    trust_state: DeviceTrustState = DeviceTrustState.TRUSTED
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class DeviceAuthChallenge(BaseModel):
    challenge_id: str
    device_id: str
    nonce: str
    created_at: float = Field(default_factory=time.time)
    expires_at: float


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600  # 1 hour


class CloudSession(BaseModel):
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
    user_agent: str = "JARVIS Cloud Client"


class AuditLogEntry(BaseModel):
    log_id: str
    event_type: str
    user_id: Optional[str] = None
    device_id: Optional[str] = None
    action: str
    status: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class CloudSecurityStatus(BaseModel):
    service: str = "JARVIS Cloud Platform"
    environment: str = "development"
    database_connected: bool = True
    active_users: int = 0
    registered_devices: int = 0
    active_sessions: int = 0
    schema_version: str = "v1_cloud_backend"
    security_architecture: str = "Ed25519 Signed Challenge + JWT Access Tokens"
