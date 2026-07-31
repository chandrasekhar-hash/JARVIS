"""
JARVIS Product 1.8 - Workspace Integration Tools.
Exposes Workspace Integration capabilities to Product 1.5 Tool Execution Engine.
"""

from typing import List, Dict, Any
from ...tools import ToolMetadata, ToolCategory, ToolCapability
from ..models import AuthType


def integration_register_connector_handler(provider: str, display_name: str, description: str, owner_id: str = "default_user", **kwargs) -> Dict[str, Any]:
    from ..integration_engine import workspace_integration_manager_instance
    connector = workspace_integration_manager_instance.register_connector(
        provider=provider,
        display_name=display_name,
        description=description,
        owner_id=owner_id,
    )
    return {
        "status": "success",
        "connector_id": connector.connector_id,
        "provider": connector.provider,
        "connector_status": connector.status.value,
    }


def integration_authenticate_handler(connector_id: str, raw_credentials: Dict[str, Any], owner_id: str = "default_user", **kwargs) -> Dict[str, Any]:
    from ..integration_engine import workspace_integration_manager_instance
    connector = workspace_integration_manager_instance.authenticate_connector(
        connector_id=connector_id,
        owner_id=owner_id,
        raw_credentials=raw_credentials,
    )
    secret_ref = connector.secret_handle.secret_ref if connector.secret_handle else None
    return {
        "status": "success",
        "connector_id": connector.connector_id,
        "connector_status": connector.status.value,
        "secret_ref": secret_ref,
    }


def integration_sync_handler(connector_id: str, owner_id: str = "default_user", **kwargs) -> Dict[str, Any]:
    from ..integration_engine import workspace_integration_manager_instance
    checkpoint = workspace_integration_manager_instance.sync_connector(connector_id=connector_id, owner_id=owner_id)
    return {
        "status": "success",
        "connector_id": checkpoint.connector_id,
        "items_synced": checkpoint.items_synced,
        "cursor_token": checkpoint.cursor_token,
    }


def integration_list_connectors_handler(owner_id: str = "default_user", provider: str = None, **kwargs) -> Dict[str, Any]:
    from ..integration_engine import workspace_integration_manager_instance
    connectors = workspace_integration_manager_instance.list_connectors(owner_id=owner_id, provider=provider)
    return {
        "status": "success",
        "count": len(connectors),
        "connectors": [
            {
                "connector_id": c.connector_id,
                "provider": c.provider,
                "display_name": c.display_name,
                "status": c.status.value,
                "circuit_state": c.circuit_state.value,
            }
            for c in connectors
        ],
    }


def get_workspace_integration_tool_metadatas() -> List[ToolMetadata]:
    return [
        ToolMetadata(
            tool_id="integration_register_connector",
            name="Register Workspace Connector",
            description="Registers a new workspace connector framework specification.",
            category=ToolCategory.UTILITY,
            capabilities=[ToolCapability.FILESYSTEM_WRITE.value],
            safety_level="safe",
            input_schema={
                "type": "object",
                "properties": {
                    "provider": {"type": "string"},
                    "display_name": {"type": "string"},
                    "description": {"type": "string"},
                    "owner_id": {"type": "string"},
                },
                "required": ["provider", "display_name", "description"],
            },
            handler=integration_register_connector_handler,
            owner="workspace_integrations",
        ),
        ToolMetadata(
            tool_id="integration_authenticate",
            name="Authenticate Workspace Connector",
            description="Authenticates a connector with credentials and issues an opaque SecretHandle.",
            category=ToolCategory.UTILITY,
            capabilities=[ToolCapability.FILESYSTEM_WRITE.value],
            safety_level="confirmation_required",
            input_schema={
                "type": "object",
                "properties": {
                    "connector_id": {"type": "string"},
                    "raw_credentials": {"type": "object"},
                    "owner_id": {"type": "string"},
                },
                "required": ["connector_id", "raw_credentials"],
            },
            handler=integration_authenticate_handler,
            owner="workspace_integrations",
        ),
        ToolMetadata(
            tool_id="integration_sync",
            name="Sync Workspace Connector",
            description="Executes data synchronization for a connected workspace platform.",
            category=ToolCategory.UTILITY,
            capabilities=[ToolCapability.NETWORK_OUTBOUND.value],
            safety_level="safe",
            input_schema={
                "type": "object",
                "properties": {
                    "connector_id": {"type": "string"},
                    "owner_id": {"type": "string"},
                },
                "required": ["connector_id"],
            },
            handler=integration_sync_handler,
            owner="workspace_integrations",
        ),
        ToolMetadata(
            tool_id="integration_list_connectors",
            name="List Workspace Connectors",
            description="Lists all registered and connected workspace platforms.",
            category=ToolCategory.UTILITY,
            capabilities=[ToolCapability.READ_ONLY.value],
            safety_level="safe",
            input_schema={
                "type": "object",
                "properties": {
                    "owner_id": {"type": "string"},
                    "provider": {"type": "string"},
                },
            },
            handler=integration_list_connectors_handler,
            owner="workspace_integrations",
        ),
    ]
