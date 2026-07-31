"""
JARVIS Product 1.7 - Notification Interface & Subsystem.
Provides notification abstractions for Desktop toasts, Voice alerts, and Web UI notifications.
"""

import logging
from typing import List
from .interfaces import INotificationChannel

logger = logging.getLogger(__name__)


class DesktopNotifier(INotificationChannel):
    def send_notification(self, title: str, message: str, level: str = "info") -> bool:
        logger.info(f"[Desktop Notification] [{level.upper()}] {title}: {message}")
        return True


class VoiceNotifier(INotificationChannel):
    def send_notification(self, title: str, message: str, level: str = "info") -> bool:
        logger.info(f"[Voice Alert] [{level.upper()}] {title}: {message}")
        return True


class WebUINotifier(INotificationChannel):
    def send_notification(self, title: str, message: str, level: str = "info") -> bool:
        logger.info(f"[Web UI Toast] [{level.upper()}] {title}: {message}")
        return True


class NotificationInterface:
    def __init__(self):
        self.channels: List[INotificationChannel] = [
            DesktopNotifier(),
            VoiceNotifier(),
            WebUINotifier(),
        ]

    def dispatch(self, title: str, message: str, level: str = "info") -> bool:
        success = True
        for channel in self.channels:
            try:
                channel.send_notification(title, message, level)
            except Exception as e:
                logger.error(f"Notification dispatch failed: {e}")
                success = False
        return success


notification_interface = NotificationInterface()
