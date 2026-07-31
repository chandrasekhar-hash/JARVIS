"""
JARVIS Product 1.8 - Connector Registry.
In-memory and SQLite-backed database storage for Workspace Connectors and metadata.
"""

import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional
from .interfaces import IConnectorRegistry
from .models import (
    WorkspaceConnector,
    AuthType,
    ConnectorStatus,
    CircuitState,
    ProviderCapabilities,
    RateLimitConfig,
    ConnectorActionSchema,
    ConnectorEventSchema,
    ConnectorPermissions,
    SecretHandle,
)

logger = logging.getLogger(__name__)


class ConnectorRegistry(IConnectorRegistry):
    def __init__(self, db_path: str = "logs/jarvis_integrations.db"):
        self.db_path = db_path
        self._memory_connectors: Dict[str, WorkspaceConnector] = {}

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        conn = self._get_connection()
        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS workspace_connectors (
                        connector_id TEXT PRIMARY KEY,
                        provider TEXT NOT NULL,
                        display_name TEXT NOT NULL,
                        description TEXT NOT NULL,
                        active_capability_version TEXT NOT NULL,
                        supported_capability_versions_json TEXT NOT NULL,
                        auth_type TEXT NOT NULL,
                        secret_ref TEXT,
                        provider_capabilities_json TEXT,
                        permissions_json TEXT,
                        status TEXT NOT NULL,
                        circuit_state TEXT NOT NULL,
                        rate_limits_json TEXT,
                        supported_actions_json TEXT,
                        supported_events_json TEXT,
                        configuration_json TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_conn_provider ON workspace_connectors(provider);")
        finally:
            conn.close()

    def register_connector(self, connector: WorkspaceConnector) -> bool:
        self._memory_connectors[connector.connector_id] = connector
        conn = self._get_connection()
        try:
            with conn:
                secret_ref_str = connector.secret_handle.secret_ref if connector.secret_handle else None
                conn.execute(
                    """
                    INSERT OR REPLACE INTO workspace_connectors (
                        connector_id, provider, display_name, description, active_capability_version,
                        supported_capability_versions_json, auth_type, secret_ref, provider_capabilities_json,
                        permissions_json, status, circuit_state, rate_limits_json, supported_actions_json,
                        supported_events_json, configuration_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        connector.connector_id,
                        connector.provider,
                        connector.display_name,
                        connector.description,
                        connector.active_capability_version,
                        json.dumps(connector.supported_capability_versions),
                        connector.auth_type.value,
                        secret_ref_str,
                        json.dumps(connector.provider_capabilities.to_dict()),
                        json.dumps(connector.permissions.to_dict()),
                        connector.status.value,
                        connector.circuit_state.value,
                        json.dumps(connector.rate_limits.to_dict()),
                        json.dumps([a.to_dict() for a in connector.supported_actions]),
                        json.dumps([e.to_dict() for e in connector.supported_events]),
                        json.dumps(connector.configuration),
                        connector.created_at.isoformat(),
                        connector.updated_at.isoformat(),
                    ),
                )
            return True
        except Exception as e:
            logger.error(f"register_connector error: {e}")
            return False
        finally:
            conn.close()

    def get_connector(self, connector_id: str) -> Optional[WorkspaceConnector]:
        if connector_id in self._memory_connectors:
            return self._memory_connectors[connector_id]

        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT * FROM workspace_connectors WHERE connector_id = ?", (connector_id,))
            row = cursor.fetchone()
            if not row:
                return None
            conn_obj = self._row_to_connector(row)
            self._memory_connectors[conn_obj.connector_id] = conn_obj
            return conn_obj
        finally:
            conn.close()

    def list_connectors(self, owner_id: Optional[str] = None, provider: Optional[str] = None) -> List[WorkspaceConnector]:
        conn = self._get_connection()
        try:
            query = "SELECT * FROM workspace_connectors WHERE 1=1"
            params = []
            if provider:
                query += " AND provider = ?"
                params.append(provider)
            query += " ORDER BY created_at DESC"

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            connectors = [self._row_to_connector(r) for r in rows]
            if owner_id:
                connectors = [c for c in connectors if c.permissions.owner_id == owner_id]
            return connectors
        finally:
            conn.close()

    def _row_to_connector(self, row: sqlite3.Row) -> WorkspaceConnector:
        from datetime import datetime
        versions = json.loads(row["supported_capability_versions_json"]) if row["supported_capability_versions_json"] else ["v1"]
        caps_dict = json.loads(row["provider_capabilities_json"]) if row["provider_capabilities_json"] else {}
        perms_dict = json.loads(row["permissions_json"]) if row["permissions_json"] else {}
        rate_dict = json.loads(row["rate_limits_json"]) if row["rate_limits_json"] else {}
        act_list = json.loads(row["supported_actions_json"]) if row["supported_actions_json"] else []
        evt_list = json.loads(row["supported_events_json"]) if row["supported_events_json"] else []
        config_dict = json.loads(row["configuration_json"]) if row["configuration_json"] else {}

        secret_handle = None
        if row["secret_ref"]:
            secret_handle = SecretHandle(
                secret_ref=row["secret_ref"],
                owner_id=perms_dict.get("owner_id", "system"),
                connector_id=row["connector_id"],
                auth_type=AuthType(row["auth_type"]),
            )

        return WorkspaceConnector(
            connector_id=row["connector_id"],
            provider=row["provider"],
            display_name=row["display_name"],
            description=row["description"],
            active_capability_version=row["active_capability_version"],
            supported_capability_versions=versions,
            auth_type=AuthType(row["auth_type"]),
            secret_handle=secret_handle,
            provider_capabilities=ProviderCapabilities.from_dict(caps_dict),
            permissions=ConnectorPermissions.from_dict(perms_dict),
            status=ConnectorStatus(row["status"]),
            circuit_state=CircuitState(row["circuit_state"]),
            rate_limits=RateLimitConfig.from_dict(rate_dict),
            supported_actions=[ConnectorActionSchema.from_dict(a) for a in act_list],
            supported_events=[ConnectorEventSchema.from_dict(e) for e in evt_list],
            configuration=config_dict,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
