import time
import uuid
import logging
from typing import Dict, Any, List, Optional
from Cloud.websocket.protocol import SyncMessageEnvelope, MessageType
from Cloud.websocket.manager import ws_manager

logger = logging.getLogger("JARVIS_NotificationMeshService")


class NotificationMeshService:
    """
    NotificationMeshService managing proactive notification dispatches.
    Broadcasts real-time notifications to active WebSocket connection channels for target user
    and stores unread notifications for offline delivery.
    """

    def __init__(self):
        # user_id -> List[Dict[str, Any]]
        self._notifications: Dict[str, List[Dict[str, Any]]] = {}

    async def dispatch_notification(
        self,
        user_id: str,
        title: str,
        body: str,
        category: str = "info",
        target_device_id: Optional[str] = None
    ) -> Dict[str, Any]:
        notif_id = f"ntf_{uuid.uuid4().hex[:12]}"
        now = time.time()

        notif_item = {
            "notification_id": notif_id,
            "user_id": user_id,
            "target_device_id": target_device_id,
            "title": title,
            "body": body,
            "category": category,
            "status": "unread",
            "created_at": now
        }

        user_notifs = self._notifications.setdefault(user_id, [])
        user_notifs.append(notif_item)
        logger.info(f"Dispatched notification '{notif_id}' ('{title}') for user '{user_id}'")

        # Broadcast over WebSocket gateway
        try:
            env = SyncMessageEnvelope(
                user_id=user_id,
                device_id=target_device_id or "system",
                message_type=MessageType.NOTIFICATION,
                payload=notif_item
            )
            await ws_manager.broadcast(env, exclude_device_id=None)
        except Exception as e:
            logger.warning(f"WebSocket broadcast error for notification '{notif_id}': {e}")

        return notif_item

    def get_notifications(self, user_id: str, unread_only: bool = True) -> List[Dict[str, Any]]:
        notifs = self._notifications.get(user_id, [])
        if unread_only:
            return [n for n in notifs if n["status"] == "unread"]
        return notifs

    def mark_as_read(self, user_id: str, notification_id: str) -> bool:
        notifs = self._notifications.get(user_id, [])
        for n in notifs:
            if n["notification_id"] == notification_id:
                n["status"] = "read"
                return True
        return False


notification_service = NotificationMeshService()
