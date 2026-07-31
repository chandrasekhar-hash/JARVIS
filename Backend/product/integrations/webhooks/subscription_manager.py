"""
JARVIS Product 1.8 - Event Subscription Manager.
Routes normalized WorkspaceEvent objects directly to Product 1.7 Automation Engine TriggerEngine.
"""

import logging
from typing import Dict, Any
from ..models import WorkspaceEvent

logger = logging.getLogger(__name__)


class EventSubscriptionManager:
    def __init__(self):
        pass

    def dispatch_event_to_automation(self, event: WorkspaceEvent) -> bool:
        topic_name = f"connector_event.{event.provider}.{event.event_type}"
        logger.info(f"[SubscriptionManager] Dispatching event '{event.event_id}' to Automation Engine topic '{topic_name}'...")

        # Routable payload structure for P1.7 Automation Engine
        try:
            from ...automation import automation_manager_instance
            automation_manager_instance.scheduler.event_watcher.on_event_emitted(
                topic=topic_name,
                payload=event.payload,
            )
            return True
        except Exception as e:
            logger.warning(f"Event dispatch to Automation Engine notice: {e}")
            return False
