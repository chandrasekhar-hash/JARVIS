"""
JARVIS Product 1.8 - Connector Lifecycle Manager.
Manages connector state machine transitions and auto-registers action capabilities as P1.5 Tools.
"""

import logging
from typing import Dict, Any, Optional
from .models import WorkspaceConnector, ConnectorStatus, AuthType
from .registry import ConnectorRegistry
from .security import CredentialManager, OAuthManager
from ..tools import tool_execution_manager_instance, ToolMetadata, ToolCategory, ToolCapability
from .logging import integration_logger

logger = logging.getLogger(__name__)


class ConnectorLifecycleManager:
    def __init__(
        self,
        registry: ConnectorRegistry,
        credential_manager: CredentialManager,
        oauth_manager: OAuthManager,
    ):
        self.registry = registry
        self.credential_manager = credential_manager
        self.oauth_manager = oauth_manager

    def register_connector_tools_with_p15(self, connector: WorkspaceConnector) -> None:
        for action in connector.supported_actions:
            tool_id = f"conn_{connector.provider}_{action.action_id}"
            
            def create_handler(p_name: str, act_id: str):
                def handler(**kwargs):
                    return {
                        "status": "success",
                        "provider": p_name,
                        "action": act_id,
                        "result": f"Executed action '{act_id}' on provider '{p_name}'.",
                    }
                return handler

            tool_meta = ToolMetadata(
                tool_id=tool_id,
                name=f"{connector.display_name}: {action.display_name}",
                description=f"{action.description} (Version: {action.capability_version})",
                category=ToolCategory.UTILITY,
                capabilities=[ToolCapability.NETWORK_OUTBOUND.value],
                safety_level=action.safety_level,
                input_schema=action.input_schema,
                output_schema=action.output_schema,
                handler=create_handler(connector.provider, action.action_id),
                owner="workspace_integrations",
                source="connector",
            )
            
            tool_execution_manager_instance.metadata_registry.register_tool_metadata(tool_meta)
            logger.info(f"Registered connector action tool '{tool_id}' with Product 1.5 Engine.")

    def authenticate_connector(
        self,
        connector_id: str,
        owner_id: str,
        raw_credentials: Dict[str, Any],
    ) -> WorkspaceConnector:
        connector = self.registry.get_connector(connector_id)
        if not connector:
            raise ValueError(f"Connector '{connector_id}' not found.")

        # Issue SecretHandle and store in vault
        secret_handle = self.credential_manager.issue_secret_handle(
            owner_id=owner_id,
            connector_id=connector_id,
            raw_credentials=raw_credentials,
        )

        connector.secret_handle = secret_handle
        connector.status = ConnectorStatus.CONNECTED
        self.registry.register_connector(connector)

        # Register connector tools with Product 1.5 Engine
        self.register_connector_tools_with_p15(connector)

        integration_logger.log_event(
            event_name="CONNECTOR_AUTHENTICATED",
            user_id=owner_id,
            connector_id=connector_id,
            provider=connector.provider,
            secret_ref=secret_handle.secret_ref,
        )
        return connector

    def revoke_connector(self, connector_id: str, owner_id: str) -> bool:
        connector = self.registry.get_connector(connector_id)
        if not connector:
            return False

        if connector.secret_handle:
            self.credential_manager.revoke_secret_handle(connector.secret_handle.secret_ref)
            connector.secret_handle = None

        connector.status = ConnectorStatus.REVOKED
        self.registry.register_connector(connector)
        integration_logger.log_event("CONNECTOR_REVOKED", owner_id, connector_id, connector.provider)
        return True
