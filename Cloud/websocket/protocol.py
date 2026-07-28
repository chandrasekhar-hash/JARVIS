import time
import uuid
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class MessageType(str, Enum):
    # Core Protocol Message Types
    AUTH = "AUTH"
    AUTH_OK = "AUTH_OK"
    SYNC_REQUEST = "SYNC_REQUEST"
    SYNC_RESPONSE = "SYNC_RESPONSE"
    DELTA = "DELTA"
    ACK = "ACK"
    PING = "PING"
    PONG = "PONG"
    DEVICE_JOIN = "DEVICE_JOIN"
    DEVICE_LEAVE = "DEVICE_LEAVE"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"

    # Reserved Message Types (Forward Compatibility)
    PLUGIN_SYNC = "PLUGIN_SYNC"
    VOICE_SYNC = "VOICE_SYNC"
    FILE_SYNC = "FILE_SYNC"
    MODEL_SYNC = "MODEL_SYNC"
    NOTIFICATION = "NOTIFICATION"


class SyncMessageEnvelope(BaseModel):
    protocol_version: str = "2.0"
    minimum_supported_version: str = "1.0"
    capabilities: List[str] = Field(
        default_factory=lambda: ["delta-sync", "crdt", "compression", "aes-gcm", "replay", "presence"]
    )
    message_id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:16]}")
    sequence_number: int = 1
    timestamp: float = Field(default_factory=time.time)
    user_id: str = ""
    device_id: str = ""
    session_id: str = ""
    message_type: MessageType = MessageType.UNKNOWN
    payload: Dict[str, Any] = Field(default_factory=dict)
