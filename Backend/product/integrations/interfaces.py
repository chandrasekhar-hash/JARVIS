"""
JARVIS Product 1.8 - Workspace Integrations Interfaces.

Defines abstract contracts for Workspace Integration Management, Registries, Credential Handles, Webhooks, Syncing, Circuit Breakers, Sandboxes, and Health Monitors.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from .models import (
    WorkspaceConnector,
    SecretHandle,
    WorkspaceEvent,
    SyncCheckpoint,
    ConnectorStatus,
    CircuitState,
)


class IConnectorRegistry(ABC):
    @abstractmethod
    def initialize(self) -> None:
        pass

    @abstractmethod
    def register_connector(self, connector: WorkspaceConnector) -> bool:
        pass

    @abstractmethod
    def get_connector(self, connector_id: str) -> Optional[WorkspaceConnector]:
        pass

    @abstractmethod
    def list_connectors(
        self,
        owner_id: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> List[WorkspaceConnector]:
        pass


class ICredentialManager(ABC):
    @abstractmethod
    def issue_secret_handle(
        self,
        owner_id: str,
        connector_id: str,
        raw_credentials: Dict[str, Any],
    ) -> SecretHandle:
        pass

    @abstractmethod
    def resolve_secret_handle(self, secret_ref: str, owner_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def revoke_secret_handle(self, secret_ref: str) -> bool:
        pass


class ICircuitBreaker(ABC):
    @abstractmethod
    def get_state(self, connector_id: str) -> CircuitState:
        pass

    @abstractmethod
    def record_success(self, connector_id: str) -> None:
        pass

    @abstractmethod
    def record_failure(self, connector_id: str) -> CircuitState:
        pass


class IWebhookManager(ABC):
    @abstractmethod
    def process_incoming_webhook(
        self,
        connector_id: str,
        raw_payload: str,
        signature_header: Optional[str] = None,
    ) -> Optional[WorkspaceEvent]:
        pass


class ISyncManager(ABC):
    @abstractmethod
    def execute_sync(self, connector: WorkspaceConnector, owner_id: str) -> SyncCheckpoint:
        pass


class IHealthMonitor(ABC):
    @abstractmethod
    def check_connector_health(self, connector: WorkspaceConnector) -> ConnectorStatus:
        pass
