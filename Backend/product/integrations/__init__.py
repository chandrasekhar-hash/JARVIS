"""
JARVIS Product 1.8 - Workspace Integrations Framework.
"""

from .models import (
    WorkspaceConnector,
    AuthType,
    ConnectorStatus,
    CircuitState,
    SecretHandle,
    ProviderCapabilities,
    RateLimitConfig,
    ConnectorActionSchema,
    ConnectorEventSchema,
    ConnectorPermissions,
    WorkspaceEvent,
    SyncCheckpoint,
)
from .integration_engine import (
    WorkspaceIntegrationManager,
    workspace_integration_manager_instance,
)
from .registry import ConnectorRegistry
from .circuit_breaker import CircuitBreakerManager
from .sandbox import ConnectorSandbox
from .security import CredentialManager, OAuthManager, secret_handle_resolver
from .webhooks import WebhookManager, EventSubscriptionManager
from .sync import SyncManager
from .health import ConnectionHealthMonitor
from .lifecycle import ConnectorLifecycleManager

__all__ = [
    "WorkspaceConnector",
    "AuthType",
    "ConnectorStatus",
    "CircuitState",
    "SecretHandle",
    "ProviderCapabilities",
    "RateLimitConfig",
    "ConnectorActionSchema",
    "ConnectorEventSchema",
    "ConnectorPermissions",
    "WorkspaceEvent",
    "SyncCheckpoint",
    "WorkspaceIntegrationManager",
    "workspace_integration_manager_instance",
    "ConnectorRegistry",
    "CircuitBreakerManager",
    "ConnectorSandbox",
    "CredentialManager",
    "OAuthManager",
    "secret_handle_resolver",
    "WebhookManager",
    "EventSubscriptionManager",
    "SyncManager",
    "ConnectionHealthMonitor",
    "ConnectorLifecycleManager",
]
