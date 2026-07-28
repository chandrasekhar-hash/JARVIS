import time
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("JARVIS_Client_ConflictHandler")


class ConflictReviewNotification(BaseModel):
    conflict_id: str
    entity_type: str
    key: str
    local_value: Any
    remote_value: Any
    merge_result: Any
    timestamp: float = Field(default_factory=time.time)
    device_source: str = ""
    resolved_automatically: bool = True
    manual_resolution: Optional[str] = None  # "local", "remote", None


class ConflictHandler:
    """
    Client ConflictHandler managing CRDT automatic resolution, producing review notifications,
    and handling manual user override choices ("local" / "remote").
    """

    def __init__(self):
        self.notifications: List[ConflictReviewNotification] = []
        self.total_conflicts_resolved = 0

    def resolve_settings_update(self, changes: Dict[str, Any], timestamp: float, device_id: str) -> int:
        from Cloud.sync.crdt import crdt_engine
        conflicts = crdt_engine.merge_settings(changes, timestamp, device_id)
        self.total_conflicts_resolved += conflicts
        return conflicts

    def resolve_memory_update(self, changes: Dict[str, Any], timestamp: float, device_id: str) -> int:
        from Cloud.sync.crdt import crdt_engine
        conflicts = crdt_engine.merge_memory(changes, timestamp, device_id)
        self.total_conflicts_resolved += conflicts
        return conflicts

    def resolve_tasks_update(self, or_set_dict: Dict[str, Any]):
        from Cloud.sync.crdt import crdt_engine
        crdt_engine.merge_tasks(or_set_dict)

    def create_review_notification(
        self,
        entity_type: str,
        key: str,
        local_val: Any,
        remote_val: Any,
        merge_res: Any,
        device_source: str
    ) -> ConflictReviewNotification:
        notif = ConflictReviewNotification(
            conflict_id=f"cnf_{int(time.time()*1000)}_{key}",
            entity_type=entity_type,
            key=key,
            local_value=local_val,
            remote_value=remote_val,
            merge_result=merge_res,
            device_source=device_source,
            resolved_automatically=True
        )
        self.notifications.append(notif)
        logger.info(f"Conflict review notification created for '{key}' from device '{device_source}'")
        return notif

    def user_override_local(self, conflict_id: str) -> bool:
        """
        User chooses to keep local state. Re-applies local value into local CRDT.
        """
        for n in self.notifications:
            if n.conflict_id == conflict_id:
                n.manual_resolution = "local"
                from Cloud.sync.crdt import crdt_engine
                if n.entity_type == "settings" and isinstance(n.local_value, dict):
                    crdt_engine.merge_settings(n.local_value, time.time(), "user_override")
                logger.info(f"User manually overrode conflict '{conflict_id}' to keep LOCAL value.")
                return True
        return False

    def user_override_remote(self, conflict_id: str) -> bool:
        """
        User chooses to accept remote state. Re-applies remote value into local CRDT.
        """
        for n in self.notifications:
            if n.conflict_id == conflict_id:
                n.manual_resolution = "remote"
                from Cloud.sync.crdt import crdt_engine
                if n.entity_type == "settings" and isinstance(n.remote_value, dict):
                    crdt_engine.merge_settings(n.remote_value, time.time(), n.device_source)
                logger.info(f"User manually overrode conflict '{conflict_id}' to accept REMOTE value.")
                return True
        return False

    def get_notifications(self) -> List[ConflictReviewNotification]:
        return self.notifications


conflict_handler = ConflictHandler()
