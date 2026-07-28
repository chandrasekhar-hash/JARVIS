import time
import uuid
from typing import Optional, Dict, Any
from fastapi import WebSocket
from websocket.state_machine import ConnectionStateMachine, ConnectionState


class WSConnection:
    def __init__(self, websocket: WebSocket, connection_id: Optional[str] = None):
        self.connection_id = connection_id or f"conn_{uuid.uuid4().hex[:12]}"
        self.websocket = websocket
        self.state_machine = ConnectionStateMachine(self.connection_id, ConnectionState.CONNECTING)
        self.user_id: str = ""
        self.device_id: str = ""
        self.session_id: str = ""
        self.connected_at: float = time.time()
        self.last_ping: float = time.time()
        self.is_alive: bool = True
        self.sequence_counter: int = 0

    @property
    def state(self) -> ConnectionState:
        return self.state_machine.current_state

    def next_sequence_number(self) -> int:
        self.sequence_counter += 1
        return self.sequence_counter

    def update_ping(self):
        self.last_ping = time.time()
        self.is_alive = True

    def transition_to(self, new_state: ConnectionState) -> bool:
        return self.state_machine.transition_to(new_state)
