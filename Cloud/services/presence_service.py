import time
import logging
from typing import Dict, Any, Optional
from websocket.protocol import SyncMessageEnvelope, MessageType
from websocket.manager import ws_manager

logger = logging.getLogger("JARVIS_Cloud_Presence")


class PresenceService:
    """
    PresenceService tracking device status (CONNECTED, ACTIVE, IDLE, AWAY, OFFLINE) and broadcasting
    presence updates ONLY on state changes (avoiding overhead on routine 15s heartbeats).
    """

    def __init__(self):
        # device_id -> {"status": str, "user_id": str, "last_state_change": float}
        self.device_presence: Dict[str, Dict[str, Any]] = {}

    async def update_presence(self, device_id: str, user_id: str, new_status: str):
        current = self.device_presence.get(device_id, {})
        old_status = current.get("status")

        if old_status != new_status:
            now = time.time()
            self.device_presence[device_id] = {
                "status": new_status,
                "user_id": user_id,
                "last_state_change": now
            }
            logger.info(f"Presence state change for Device '{device_id}': {old_status} -> {new_status}")

            msg_type = MessageType.DEVICE_JOIN if new_status in ["CONNECTED", "ACTIVE"] else MessageType.DEVICE_LEAVE
            env = SyncMessageEnvelope(
                user_id=user_id,
                device_id=device_id,
                message_type=msg_type,
                payload={
                    "status": new_status,
                    "old_status": old_status,
                    "timestamp": now
                }
            )
            # Broadcast state change to other user devices
            await ws_manager.broadcast(env, exclude_device_id=device_id)

    def get_presence(self, device_id: str) -> Optional[Dict[str, Any]]:
        return self.device_presence.get(device_id)


presence_service = PresenceService()
