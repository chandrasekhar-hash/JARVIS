import logging
from typing import Optional, Dict, Any, Tuple
from services.security_service import security_service
from websocket.connection import WSConnection
from websocket.state_machine import ConnectionState

logger = logging.getLogger("JARVIS_Cloud_WSAuth")


def authenticate_websocket_connection(
    conn: WSConnection,
    token: str,
    protocol_version: str = "2.0"
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Validates JWT token and protocol version compatibility for WebSocket connections.
    """
    conn.transition_to(ConnectionState.AUTHENTICATING)

    # Version check
    if not protocol_version or not protocol_version.startswith("2."):
        logger.warning(f"Unsupported protocol version '{protocol_version}' from connection {conn.connection_id}")
        conn.transition_to(ConnectionState.DISCONNECTED)
        return False, None, "Unsupported protocol version. Minimum supported version is 2.0"

    payload = security_service.validate_access_token(token)
    if not payload:
        logger.warning(f"Invalid or expired JWT token for connection {conn.connection_id}")
        conn.transition_to(ConnectionState.DISCONNECTED)
        return False, None, "Invalid or expired session access token"

    conn.user_id = payload.get("sub", "")
    conn.device_id = payload.get("dev", "")
    conn.session_id = payload.get("ses", "")

    conn.transition_to(ConnectionState.ACTIVE)
    logger.info(f"WS [{conn.connection_id}] Auth SUCCESS for User '{conn.user_id}', Device '{conn.device_id}'")
    return True, payload, "Authenticated"
