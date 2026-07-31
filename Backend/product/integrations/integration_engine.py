"""
JARVIS Product 1.8 - Master Workspace Integration Manager Entrypoint.
Initializes ConnectorRegistry, CredentialManager, OAuthManager, WebhookManager, SyncManager, and HealthMonitor.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from .models import WorkspaceConnector, AuthType, ProviderCapabilities, ConnectorActionSchema, ConnectorEventSchema, ConnectorStatus, SecretHandle
from .registry import ConnectorRegistry
from .security import CredentialManager, OAuthManager, secret_handle_resolver
from .circuit_breaker import CircuitBreakerManager
from .rate_limiter import RateLimitManager
from .client_factory import APIClientFactory
from .webhooks import WebhookManager, EventSubscriptionManager
from .sync import SyncManager
from .health import ConnectionHealthMonitor
from .lifecycle import ConnectorLifecycleManager
from .telemetry import integration_telemetry

logger = logging.getLogger(__name__)


class WorkspaceIntegrationManager:
    def __init__(self, db_path: str = "logs/jarvis_integrations.db"):
        self.db_path = db_path

        # 1. Registry & Security
        self.registry = ConnectorRegistry(db_path=db_path)
        self.credential_manager = CredentialManager()
        self.oauth_manager = OAuthManager(credential_manager=self.credential_manager)

        # 2. Resilience & Clients
        self.circuit_breaker = CircuitBreakerManager()
        self.rate_limiter = RateLimitManager()
        self.client_factory = APIClientFactory(
            credential_manager=self.credential_manager,
            circuit_breaker=self.circuit_breaker,
            rate_limiter=self.rate_limiter,
        )

        # 3. Lifecycle, Webhooks & Sync
        self.lifecycle_manager = ConnectorLifecycleManager(
            registry=self.registry,
            credential_manager=self.credential_manager,
            oauth_manager=self.oauth_manager,
        )
        self.webhook_manager = WebhookManager()
        self.subscription_manager = EventSubscriptionManager()
        self.sync_manager = SyncManager(api_client_factory=self.client_factory)
        self.health_monitor = ConnectionHealthMonitor(circuit_breaker=self.circuit_breaker)

        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return

        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        self.registry.initialize()
        self._initialized = True
        logger.info("JARVIS Workspace Integrations Framework Product 1.8 initialized successfully.")

    # High-level Public API Methods
    def register_connector(
        self,
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
    ) -> WorkspaceConnector:
        self.initialize()
        connector = WorkspaceConnector.create_new(
            provider=provider,
            display_name=display_name,
            description=description,
            owner_id=owner_id,
            auth_type=auth_type,
            active_capability_version=active_capability_version,
            supported_capability_versions=supported_capability_versions,
            provider_capabilities=provider_capabilities,
            supported_actions=supported_actions,
            supported_events=supported_events,
        )
        self.registry.register_connector(connector)
        integration_telemetry.record_connection()
        return connector

    def authenticate_connector(self, connector_id: str, owner_id: str, raw_credentials: Dict[str, Any]) -> WorkspaceConnector:
        self.initialize()
        return self.lifecycle_manager.authenticate_connector(connector_id, owner_id, raw_credentials)

    def process_webhook(self, connector_id: str, raw_payload: str, signature_header: Optional[str] = None) -> bool:
        self.initialize()
        event = self.webhook_manager.process_incoming_webhook(connector_id, raw_payload, signature_header)
        if event:
            integration_telemetry.record_webhook()
            return self.subscription_manager.dispatch_event_to_automation(event)
        return False

    def sync_connector(self, connector_id: str, owner_id: str):
        self.initialize()
        connector = self.registry.get_connector(connector_id)
        if not connector:
            raise ValueError(f"Connector '{connector_id}' not found.")
        integration_telemetry.record_sync()
        return self.sync_manager.execute_sync(connector, owner_id)

    def get_connector(self, connector_id: str) -> Optional[WorkspaceConnector]:
        self.initialize()
        return self.registry.get_connector(connector_id)

    def list_connectors(self, owner_id: Optional[str] = None, provider: Optional[str] = None) -> List[WorkspaceConnector]:
        self.initialize()
        return self.registry.list_connectors(owner_id=owner_id, provider=provider)

    def check_health(self, connector_id: str) -> ConnectorStatus:
        self.initialize()
        connector = self.registry.get_connector(connector_id)
        if not connector:
            return ConnectorStatus.REGISTERED
        return self.health_monitor.check_connector_health(connector)

    def revoke_connector(self, connector_id: str, owner_id: str) -> bool:
        self.initialize()
        return self.lifecycle_manager.revoke_connector(connector_id, owner_id)

    def get_telemetry_metrics(self) -> Dict[str, Any]:
        return integration_telemetry.get_metrics()


workspace_integration_manager_instance = WorkspaceIntegrationManager()
