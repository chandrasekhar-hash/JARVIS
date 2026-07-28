import time
import logging
from typing import Dict, Any, Optional, List
from Cloud.websocket.protocol import SyncMessageEnvelope, MessageType
from Cloud.websocket.manager import ws_manager

logger = logging.getLogger("JARVIS_Cloud_Presence")


class PresenceService:
    """
    Centralized PresenceService tracking device availability (CONNECTED, ACTIVE, IDLE, OFFLINE),
    heartbeats, hardware capabilities, active workload scores, and preferred execution nodes.
    Broadcasts presence updates only on state changes.
    """

    def __init__(self):
        # device_id -> presence metadata
        self.device_presence: Dict[str, Dict[str, Any]] = {}

    async def update_presence(
        self,
        device_id: str,
        user_id: str,
        new_status: str,
        capabilities: Optional[List[str]] = None,
        workload_score: float = 0.0,
        preferred_node: Optional[str] = None
    ):
        current = self.device_presence.get(device_id, {})
        old_status = current.get("status")
        now = time.time()

        self.device_presence[device_id] = {
            "status": new_status,
            "user_id": user_id,
            "last_heartbeat": now,
            "last_state_change": now if old_status != new_status else current.get("last_state_change", now),
            "capabilities": capabilities or current.get("capabilities", ["desktop_execution", "llm_offload"]),
            "workload_score": workload_score,
            "preferred_node": preferred_node or device_id
        }

        if old_status != new_status:
            logger.info(f"Presence state change for Device '{device_id}': {old_status} -> {new_status}")
            msg_type = MessageType.DEVICE_JOIN if new_status in ["CONNECTED", "ACTIVE"] else MessageType.DEVICE_LEAVE
            env = SyncMessageEnvelope(
                user_id=user_id,
                device_id=device_id,
                message_type=msg_type,
                payload={
                    "status": new_status,
                    "old_status": old_status,
                    "timestamp": now,
                    "capabilities": self.device_presence[device_id]["capabilities"]
                }
            )
            # Broadcast state change to other user devices
            try:
                await ws_manager.broadcast(env, exclude_device_id=device_id)
            except Exception:
                pass

    def record_heartbeat(self, device_id: str):
        if device_id in self.device_presence:
            self.device_presence[device_id]["last_heartbeat"] = time.time()

    def get_presence(self, device_id: str) -> Optional[Dict[str, Any]]:
        return self.device_presence.get(device_id)

    def is_device_online(self, device_id: str) -> bool:
        p = self.get_presence(device_id)
        if not p:
            return False
        if p["status"] in ["OFFLINE", "DISCONNECTED"]:
            return False
        # Consider stale if last heartbeat > 45s
        if time.time() - p.get("last_heartbeat", 0) > 45.0:
            return False
        return True

    def get_active_devices_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        active = []
        for dev_id, info in self.device_presence.items():
            if info.get("user_id") == user_id and self.is_device_online(dev_id):
                active.append({"device_id": dev_id, **info})
        return active


presence_service = PresenceService()
