import logging
from enum import Enum
from typing import Set, Dict

logger = logging.getLogger("JARVIS_Cloud_WSState")


class ConnectionState(str, Enum):
    CONNECTING = "CONNECTING"
    AUTHENTICATING = "AUTHENTICATING"
    SYNCHRONIZING = "SYNCHRONIZING"
    ACTIVE = "ACTIVE"
    IDLE = "IDLE"
    RECONNECTING = "RECONNECTING"
    DISCONNECTED = "DISCONNECTED"


VALID_TRANSITIONS: Dict[ConnectionState, Set[ConnectionState]] = {
    ConnectionState.CONNECTING: {ConnectionState.AUTHENTICATING, ConnectionState.DISCONNECTED},
    ConnectionState.AUTHENTICATING: {ConnectionState.SYNCHRONIZING, ConnectionState.ACTIVE, ConnectionState.DISCONNECTED},
    ConnectionState.SYNCHRONIZING: {ConnectionState.ACTIVE, ConnectionState.IDLE, ConnectionState.DISCONNECTED},
    ConnectionState.ACTIVE: {ConnectionState.IDLE, ConnectionState.SYNCHRONIZING, ConnectionState.RECONNECTING, ConnectionState.DISCONNECTED},
    ConnectionState.IDLE: {ConnectionState.ACTIVE, ConnectionState.SYNCHRONIZING, ConnectionState.RECONNECTING, ConnectionState.DISCONNECTED},
    ConnectionState.RECONNECTING: {ConnectionState.AUTHENTICATING, ConnectionState.DISCONNECTED},
    ConnectionState.DISCONNECTED: {ConnectionState.CONNECTING, ConnectionState.RECONNECTING},
}


class ConnectionStateMachine:
    def __init__(self, connection_id: str, initial_state: ConnectionState = ConnectionState.CONNECTING):
        self.connection_id = connection_id
        self._state = initial_state

    @property
    def current_state(self) -> ConnectionState:
        return self._state

    def transition_to(self, new_state: ConnectionState) -> bool:
        if new_state == self._state:
            return True

        allowed = VALID_TRANSITIONS.get(self._state, set())
        if new_state in allowed:
            logger.info(f"WS [{self.connection_id}] State transition: {self._state.value} -> {new_state.value}")
            self._state = new_state
            return True
        else:
            logger.warning(f"WS [{self.connection_id}] Invalid transition attempt: {self._state.value} -> {new_state.value}")
            return False
