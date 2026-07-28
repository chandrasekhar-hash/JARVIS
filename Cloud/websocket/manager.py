import logging
import json
from typing import Dict, List, Set, Optional
from fastapi import WebSocket
from websocket.connection import WSConnection
from websocket.state_machine import ConnectionState
from websocket.protocol import SyncMessageEnvelope

logger = logging.getLogger("JARVIS_Cloud_WSManager")


class ConnectionManager:
    """
    Production ConnectionManager tracking connection states, user session maps, and device session maps.
    """

    def __init__(self):
        self.active_connections: Dict[str, WSConnection] = {}
        self.user_sessions: Dict[str, Set[str]] = {}
        self.device_sessions: Dict[str, str] = {}

    def get_connection(self, connection_id: str) -> Optional[WSConnection]:
        return self.active_connections.get(connection_id)

    async def connect(self, conn: WSConnection):
        await conn.websocket.accept()
        self.active_connections[conn.connection_id] = conn
        logger.info(f"WS [{conn.connection_id}] Accepted connection. Total active: {len(self.active_connections)}")

    def register_authenticated_session(self, conn: WSConnection):
        if conn.user_id:
            if conn.user_id not in self.user_sessions:
                self.user_sessions[conn.user_id] = set()
            self.user_sessions[conn.user_id].add(conn.connection_id)

        if conn.device_id:
            self.device_sessions[conn.device_id] = conn.connection_id

    async def disconnect(self, conn: WSConnection):
        conn.transition_to(ConnectionState.DISCONNECTED)
        conn.is_alive = False

        if conn.connection_id in self.active_connections:
            del self.active_connections[conn.connection_id]

        if conn.user_id and conn.user_id in self.user_sessions:
            self.user_sessions[conn.user_id].discard(conn.connection_id)
            if not self.user_sessions[conn.user_id]:
                del self.user_sessions[conn.user_id]

        if conn.device_id and conn.device_id in self.device_sessions:
            if self.device_sessions[conn.device_id] == conn.connection_id:
                del self.device_sessions[conn.device_id]

        try:
            await conn.websocket.close()
        except Exception:
            pass

        logger.info(f"WS [{conn.connection_id}] Disconnected. Remaining active: {len(self.active_connections)}")

    async def send_envelope(self, conn: WSConnection, envelope: SyncMessageEnvelope):
        try:
            payload_str = json.dumps(envelope.model_dump())
            await conn.websocket.send_text(payload_str)
        except Exception as e:
            logger.error(f"Failed sending envelope to WS [{conn.connection_id}]: {e}")
            await self.disconnect(conn)

    async def send_to_device(self, device_id: str, envelope: SyncMessageEnvelope) -> bool:
        conn_id = self.device_sessions.get(device_id)
        if conn_id and conn_id in self.active_connections:
            conn = self.active_connections[conn_id]
            await self.send_envelope(conn, envelope)
            return True
        return False

    async def send_to_user(self, user_id: str, envelope: SyncMessageEnvelope) -> int:
        count = 0
        conn_ids = list(self.user_sessions.get(user_id, set()))
        for conn_id in conn_ids:
            if conn_id in self.active_connections:
                conn = self.active_connections[conn_id]
                await self.send_envelope(conn, envelope)
                count += 1
        return count

    async def broadcast(self, envelope: SyncMessageEnvelope, exclude_device_id: Optional[str] = None):
        for conn in list(self.active_connections.values()):
            if exclude_device_id and conn.device_id == exclude_device_id:
                continue
            await self.send_envelope(conn, envelope)

    def get_state_counts(self) -> Dict[str, int]:
        counts = {state.value: 0 for state in ConnectionState}
        for conn in self.active_connections.values():
            counts[conn.state.value] += 1
        return counts


ws_manager = ConnectionManager()
