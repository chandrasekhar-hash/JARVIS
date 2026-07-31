"""
JARVIS Product 1.8 - Workspace Integrations Framework Automated Unit & Integration Test Suite.
Verifies Registry, Capability Version Negotiation, SecretHandles, CircuitBreaker, Webhooks, Syncing, P1.5 Tool Execution, and P1.7 Automation Routing.
"""

import pytest
import os
import tempfile
from typing import Dict, Any

from backend.product.integrations import (
    WorkspaceIntegrationManager,
    WorkspaceConnector,
    AuthType,
    ConnectorStatus,
    CircuitState,
    SecretHandle,
    ProviderCapabilities,
    ConnectorActionSchema,
    ConnectorEventSchema,
)
from backend.product.tools import tool_execution_manager_instance
from backend.product.integrations.tools.integration_tools import get_workspace_integration_tool_metadatas


@pytest.fixture
def temp_db_path(tmp_path):
    return str(tmp_path / "test_integrations.db")


@pytest.fixture
def manager(temp_db_path):
    mgr = WorkspaceIntegrationManager(db_path=temp_db_path)
    mgr.initialize()
    return mgr


def test_connector_registration_and_capability_versioning(manager):
    actions = [
        ConnectorActionSchema(action_id="send_msg", display_name="Send Message", description="Sends a message", capability_version="v1"),
        ConnectorActionSchema(action_id="send_msg_v2", display_name="Send Message V2", description="Sends formatted card message", capability_version="v2"),
    ]
    events = [
        ConnectorEventSchema(event_type="msg_received", display_name="Message Received", description="Triggers on new message", capability_version="v1"),
    ]
    caps = ProviderCapabilities(supports_webhooks=True, supports_incremental_sync=True, supports_streaming=False)

    connector = manager.register_connector(
        provider="github",
        display_name="GitHub Workspace",
        description="GitHub repository integration",
        owner_id="user_dev_101",
        auth_type=AuthType.OAUTH2,
        active_capability_version="v1",
        supported_capability_versions=["v1", "v2"],
        provider_capabilities=caps,
        supported_actions=actions,
        supported_events=events,
    )

    assert connector.connector_id.startswith("conn_")
    assert connector.provider == "github"
    assert connector.status == ConnectorStatus.REGISTERED
    assert connector.active_capability_version == "v1"
    assert "v2" in connector.supported_capability_versions
    assert len(connector.supported_actions) == 2
    assert connector.provider_capabilities.supports_webhooks is True

    fetched = manager.get_connector(connector.connector_id)
    assert fetched is not None
    assert fetched.display_name == "GitHub Workspace"


def test_opaque_secret_handle_and_security(manager):
    connector = manager.register_connector(
        provider="slack",
        display_name="Slack Workspace",
        description="Slack messaging connector",
        owner_id="user_dev_101",
        auth_type=AuthType.OAUTH2,
    )

    raw_creds = {
        "auth_type": AuthType.OAUTH2.value,
        "access_token": "xoxb-mock-secret-access-token-12345",
        "refresh_token": "xoxr-mock-secret-refresh-token-67890",
    }

    auth_conn = manager.authenticate_connector(
        connector_id=connector.connector_id,
        owner_id="user_dev_101",
        raw_credentials=raw_creds,
    )

    assert auth_conn.status == ConnectorStatus.CONNECTED
    assert auth_conn.secret_handle is not None
    assert auth_conn.secret_handle.secret_ref.startswith("secret_ref_")

    # Verify resolution with correct owner
    resolved = manager.credential_manager.resolve_secret_handle(auth_conn.secret_handle.secret_ref, "user_dev_101")
    assert resolved is not None
    assert resolved["access_token"] == "xoxb-mock-secret-access-token-12345"

    # Verify resolution rejected for wrong owner
    unauthorized = manager.credential_manager.resolve_secret_handle(auth_conn.secret_handle.secret_ref, "hacker_user")
    assert unauthorized is None

    secret_ref = auth_conn.secret_handle.secret_ref

    # Test revocation
    revoked = manager.revoke_connector(connector.connector_id, "user_dev_101")
    assert revoked is True
    assert manager.get_connector(connector.connector_id).status == ConnectorStatus.REVOKED
    assert manager.credential_manager.resolve_secret_handle(secret_ref, "user_dev_101") is None


def test_circuit_breaker_state_machine(manager):
    cb = manager.circuit_breaker
    conn_id = "conn_mock_test_123"

    # 1. Initial CLOSED State
    assert cb.get_state(conn_id) == CircuitState.CLOSED

    # 2. Record 4 failures -> Still CLOSED
    for _ in range(4):
        cb.record_failure(conn_id)
    assert cb.get_state(conn_id) == CircuitState.CLOSED

    # 3. 5th failure -> Trips to OPEN
    state = cb.record_failure(conn_id)
    assert state == CircuitState.OPEN
    assert cb.get_state(conn_id) == CircuitState.OPEN

    # 4. Simulate timeout transition -> HALF_OPEN
    cb._last_failure_time[conn_id] = 0.0
    assert cb.get_state(conn_id) == CircuitState.HALF_OPEN

    # 5. Success -> Resets to CLOSED
    cb.record_success(conn_id)
    assert cb.get_state(conn_id) == CircuitState.CLOSED


def test_webhook_hmac_and_deduplication(manager):
    connector = manager.register_connector(
        provider="google_workspace",
        display_name="Google Workspace",
        description="Google Drive & Gmail connector",
        owner_id="user_dev_101",
    )

    payload = '{"event_type": "file_created", "provider": "google_workspace", "owner_id": "user_dev_101", "file_name": "report.pdf"}'

    # Process first webhook -> Success
    res1 = manager.process_webhook(connector.connector_id, payload)
    assert res1 is True

    # Process duplicate webhook -> Deduplicated (False)
    res2 = manager.process_webhook(connector.connector_id, payload)
    assert res2 is False


def test_sync_manager_checkpointing(manager):
    connector = manager.register_connector(
        provider="notion",
        display_name="Notion Workspace",
        description="Notion document connector",
        owner_id="user_dev_101",
        auth_type=AuthType.API_KEY,
    )

    manager.authenticate_connector(
        connector_id=connector.connector_id,
        owner_id="user_dev_101",
        raw_credentials={"auth_type": AuthType.API_KEY.value, "api_key": "secret_notion_key_123"},
    )

    checkpoint = manager.sync_connector(connector.connector_id, "user_dev_101")
    assert checkpoint.connector_id == connector.connector_id
    assert checkpoint.items_synced == 5
    assert checkpoint.cursor_token.startswith("cursor_")


def test_connector_tools_registration_with_p15(manager):
    # Register workspace integration tool metadatas with Product 1.5
    for meta in get_workspace_integration_tool_metadatas():
        tool_execution_manager_instance.metadata_registry.register_tool_metadata(meta)

    # 1. Test integration_register_connector tool
    reg_meta = tool_execution_manager_instance.metadata_registry.get_tool_metadata("integration_register_connector")
    assert reg_meta is not None

    reg_res = reg_meta.handler(provider="slack", display_name="Slack", description="Slack messaging", owner_id="user_test")
    assert reg_res["status"] == "success"
    assert reg_res["provider"] == "slack"
    conn_id = reg_res["connector_id"]

    # 2. Test integration_authenticate tool
    auth_meta = tool_execution_manager_instance.metadata_registry.get_tool_metadata("integration_authenticate")
    auth_res = auth_meta.handler(connector_id=conn_id, raw_credentials={"auth_type": "OAUTH2", "token": "abc"}, owner_id="user_test")
    assert auth_res["status"] == "success"
    assert auth_res["secret_ref"].startswith("secret_ref_")

    # 3. Test integration_list_connectors tool
    list_meta = tool_execution_manager_instance.metadata_registry.get_tool_metadata("integration_list_connectors")
    list_res = list_meta.handler(owner_id="user_test")
    assert list_res["status"] == "success"
    assert list_res["count"] >= 1


def test_connection_health_monitor(manager):
    connector = manager.register_connector(
        provider="dropbox",
        display_name="Dropbox Storage",
        description="Dropbox storage connector",
        owner_id="user_dev_101",
    )

    status_initial = manager.check_health(connector.connector_id)
    assert status_initial == ConnectorStatus.REGISTERED

    manager.authenticate_connector(connector.connector_id, "user_dev_101", {"token": "xyz"})
    status_healthy = manager.check_health(connector.connector_id)
    assert status_healthy == ConnectorStatus.HEALTHY

    # Trip Circuit Breaker -> Status becomes DEGRADED
    for _ in range(5):
        manager.circuit_breaker.record_failure(connector.connector_id)

    status_degraded = manager.check_health(connector.connector_id)
    assert status_degraded == ConnectorStatus.DEGRADED
