"""
JARVIS Product 1.9 - Voice Notification Manager.
Priority queue for spoken audio alerts with quiet-hours suppression.
"""

import queue
import logging
from typing import Dict, Any, Optional
from .models import VoiceNotification, NotificationPriority

logger = logging.getLogger(__name__)


class VoiceNotificationManager:
    def __init__(self):
        self.priority_queue = queue.PriorityQueue()
        self.quiet_hours_enabled = False

    def is_quiet_hours(self, owner_id: str) -> bool:
        return self.quiet_hours_enabled

    def enqueue_notification(self, notification: VoiceNotification) -> bool:
        if self.is_quiet_hours(notification.owner_id) and notification.priority < NotificationPriority.URGENT:
            logger.info(f"[VoiceNotificationManager] Notification '{notification.notification_id}' suppressed due to Quiet Hours.")
            return False

        # Enqueue with inverted priority value for max heap behavior in PriorityQueue
        self.priority_queue.put((-notification.priority.value, notification))
        logger.info(f"[VoiceNotificationManager] Enqueued spoken notification '{notification.notification_id}' (Priority: {notification.priority.name}).")
        return True

    def get_next_notification(self) -> Optional[VoiceNotification]:
        if self.priority_queue.empty():
            return None
        priority, notification = self.priority_queue.get()
        return notification
