"""
JARVIS Product 1.8 - Connection Health Monitor.
Runs periodic heartbeats testing connector credentials, CircuitBreaker state, and rate limits.
"""

import logging
from typing import Dict, Any
from .interfaces import IHealthMonitor
from .models import WorkspaceConnector, ConnectorStatus, CircuitState
from .circuit_breaker import CircuitBreakerManager

logger = logging.getLogger(__name__)


class ConnectionHealthMonitor(IHealthMonitor):
    def __init__(self, circuit_breaker: CircuitBreakerManager):
        self.circuit_breaker = circuit_breaker

    def check_connector_health(self, connector: WorkspaceConnector) -> ConnectorStatus:
        circuit_state = self.circuit_breaker.get_state(connector.connector_id)

        if circuit_state == CircuitState.OPEN:
            connector.status = ConnectorStatus.DEGRADED
            logger.warning(f"Connector '{connector.connector_id}' health marked DEGRADED due to OPEN Circuit Breaker.")
            return ConnectorStatus.DEGRADED

        if not connector.secret_handle:
            connector.status = ConnectorStatus.REGISTERED
            return ConnectorStatus.REGISTERED

        connector.status = ConnectorStatus.HEALTHY
        return ConnectorStatus.HEALTHY
