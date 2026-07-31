"""
JARVIS Product 1.8 - Workspace Integrations Domain Models.

Defines data classes, enums, capability versions, secret handles, and schemas for Connectors, Auth, Webhooks, Sync, and Health.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
import uuid


class AuthType(str, Enum):
    OAUTH2 = "OAUTH2"
    API_KEY = "API_KEY"
    PAT = "PAT"
    SERVICE_ACCOUNT = "SERVICE_ACCOUNT"


class ConnectorStatus(str, Enum):
    REGISTERED = "REGISTERED"
    INSTALLED = "INSTALLED"
    AUTHENTICATED = "AUTHENTICATED"
    CONNECTED = "CONNECTED"
    SYNCING = "SYNCING"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    REVOKED = "REVOKED"


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class SecretHandle:
    secret_ref: str
    owner_id: str
    connector_id: str
    auth_type: AuthType
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create_new(cls, owner_id: str, connector_id: str, auth_type: AuthType) -> "SecretHandle":
        ref = f"secret_ref_{uuid.uuid4().hex[:12]}"
        return cls(secret_ref=ref, owner_id=owner_id, connector_id=connector_id, auth_type=auth_type)


@dataclass
class ProviderCapabilities:
    supports_webhooks: bool = True
    supports_incremental_sync: bool = True
    supports_search: bool = True
    supports_push: bool = True
    supports_streaming: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "supports_webhooks": self.supports_webhooks,
            "supports_incremental_sync": self.supports_incremental_sync,
            "supports_search": self.supports_search,
            "supports_push": self.supports_push,
            "supports_streaming": self.supports_streaming,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProviderCapabilities":
        if not data:
            return cls()
        return cls(
            supports_webhooks=data.get("supports_webhooks", True),
            supports_incremental_sync=data.get("supports_incremental_sync", True),
            supports_search=data.get("supports_search", True),
            supports_push=data.get("supports_push", True),
            supports_streaming=data.get("supports_streaming", False),
        )


@dataclass
class RateLimitConfig:
    requests_per_minute: int = 120
    concurrent_requests: int = 5
    retry_after_header: str = "Retry-After"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requests_per_minute": self.requests_per_minute,
            "concurrent_requests": self.concurrent_requests,
            "retry_after_header": self.retry_after_header,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RateLimitConfig":
        if not data:
            return cls()
        return cls(
            requests_per_minute=data.get("requests_per_minute", 120),
            concurrent_requests=data.get("concurrent_requests", 5),
            retry_after_header=data.get("retry_after_header", "Retry-After"),
        )


@dataclass
class ConnectorActionSchema:
    action_id: str
    display_name: str
    description: str
    capability_version: str = "v1"
    safety_level: str = "safe"
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "display_name": self.display_name,
            "description": self.description,
            "capability_version": self.capability_version,
            "safety_level": self.safety_level,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConnectorActionSchema":
        return cls(
            action_id=data.get("action_id", ""),
            display_name=data.get("display_name", ""),
            description=data.get("description", ""),
            capability_version=data.get("capability_version", "v1"),
            safety_level=data.get("safety_level", "safe"),
            input_schema=data.get("input_schema", {}),
            output_schema=data.get("output_schema", {}),
        )


@dataclass
class ConnectorEventSchema:
    event_type: str
    display_name: str
    description: str
    capability_version: str = "v1"
    payload_schema: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "display_name": self.display_name,
            "description": self.description,
            "capability_version": self.capability_version,
            "payload_schema": self.payload_schema,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConnectorEventSchema":
        return cls(
            event_type=data.get("event_type", ""),
            display_name=data.get("display_name", ""),
            description=data.get("description", ""),
            capability_version=data.get("capability_version", "v1"),
            payload_schema=data.get("payload_schema", {}),
        )


@dataclass
class ConnectorPermissions:
    owner_id: str
    required_scopes: List[str] = field(default_factory=list)
    allowed_roles: List[str] = field(default_factory=lambda: ["admin", "user"])
    allowed_plugins: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "owner_id": self.owner_id,
            "required_scopes": self.required_scopes,
            "allowed_roles": self.allowed_roles,
            "allowed_plugins": self.allowed_plugins,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConnectorPermissions":
        if not data:
            return cls(owner_id="system")
        return cls(
            owner_id=data.get("owner_id", "system"),
            required_scopes=data.get("required_scopes", []),
            allowed_roles=data.get("allowed_roles", ["admin", "user"]),
            allowed_plugins=data.get("allowed_plugins", []),
        )


@dataclass
class WorkspaceConnector:
    connector_id: str
    provider: str
    display_name: str
    description: str
    active_capability_version: str = "v1"
    supported_capability_versions: List[str] = field(default_factory=lambda: ["v1"])
    auth_type: AuthType = AuthType.OAUTH2
    secret_handle: Optional[SecretHandle] = None
    provider_capabilities: ProviderCapabilities = field(default_factory=ProviderCapabilities)
    permissions: ConnectorPermissions = field(default_factory=lambda: ConnectorPermissions(owner_id="system"))
    status: ConnectorStatus = ConnectorStatus.REGISTERED
    circuit_state: CircuitState = CircuitState.CLOSED
    rate_limits: RateLimitConfig = field(default_factory=RateLimitConfig)
    supported_actions: List[ConnectorActionSchema] = field(default_factory=list)
    supported_events: List[ConnectorEventSchema] = field(default_factory=list)
    configuration: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create_new(
        cls,
        provider: str,
        display_name: str,
        description: str,
        owner_id: str,
        auth_type: AuthType = AuthType.OAUTH2,
        active_capability_version: str = "v1",
        supported_capability_versions: Optional[List[str]] = None,
        provider_capabilities: Optional[ProviderCapabilities] = None,
        supported_actions: Optional[List[ConnectorActionSchema]] = None,
        supported_events: Optional[List[ConnectorEventSchema]] = None,
    ) -> "WorkspaceConnector":
        conn_id = f"conn_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow()
        return cls(
            connector_id=conn_id,
            provider=provider,
            display_name=display_name,
            description=description,
            active_capability_version=active_capability_version,
            supported_capability_versions=supported_capability_versions or ["v1"],
            auth_type=auth_type,
            provider_capabilities=provider_capabilities or ProviderCapabilities(),
            permissions=ConnectorPermissions(owner_id=owner_id),
            status=ConnectorStatus.REGISTERED,
            circuit_state=CircuitState.CLOSED,
            supported_actions=supported_actions or [],
            supported_events=supported_events or [],
            created_at=now,
            updated_at=now,
        )


@dataclass
class WorkspaceEvent:
    event_id: str
    connector_id: str
    provider: str
    owner_id: str
    event_type: str
    capability_version: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SyncCheckpoint:
    connector_id: str
    owner_id: str
    last_sync_time: datetime = field(default_factory=datetime.utcnow)
    cursor_token: Optional[str] = None
    items_synced: int = 0
