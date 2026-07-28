import logging
import asyncio
from typing import Dict, Any, Optional
from Client.sync.sync_manager import client_sync_manager, ClientSyncManager
from Client.sync.scheduler import intelligent_scheduler, SyncTrigger

logger = logging.getLogger("JARVIS_Client_CloudSyncService")


class CloudSyncService:
    """
    High-level CloudSyncService API for Desktop assistant backend & Mobile client bridges.
    Provides simple, robust methods for settings, memory, and task synchronization with offline resilience.
    """

    def __init__(self, manager: Optional[ClientSyncManager] = None):
        self.sync_manager = manager or client_sync_manager

    def initialize(self, user_id: str, device_id: str, access_token: str, refresh_token: str):
        self.sync_manager.initialize_client(user_id, device_id, access_token, refresh_token)
        intelligent_scheduler.start()
        logger.info(f"CloudSyncService initialized for user '{user_id}', device '{device_id}'.")

    def sync_settings(self, settings_dict: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Syncing settings update: {settings_dict}")
        return self.sync_manager.submit_local_change("settings", settings_dict)

    def sync_memory(self, memory_dict: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Syncing memory update: {memory_dict}")
        return self.sync_manager.submit_local_change("memory", memory_dict)

    def sync_tasks(self, tasks_dict: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Syncing tasks update: {tasks_dict}")
        return self.sync_manager.submit_local_change("tasks", tasks_dict)

    def resolve_conflict(self, conflict_id: str, choice: str) -> bool:
        """
        Manually resolves a conflict given conflict_id and choice ("local" or "remote").
        """
        if choice == "local":
            return self.sync_manager.conflicts.user_override_local(conflict_id)
        elif choice == "remote":
            return self.sync_manager.conflicts.user_override_remote(conflict_id)
        return False

    def force_sync(self) -> Dict[str, Any]:
        logger.info("Manual force sync requested by user.")
        intelligent_scheduler.trigger_sync(SyncTrigger.MANUAL)
        try:
            loop = asyncio.get_running_loop()
            replayed = loop.create_task(self.sync_manager.replay_offline_queue())
        except RuntimeError:
            replayed = asyncio.run(self.sync_manager.replay_offline_queue())
        return {"status": "triggered", "replayed_offline_ops": replayed}

    def get_status(self) -> Dict[str, Any]:
        return self.sync_manager.get_status()

    def shutdown(self):
        intelligent_scheduler.stop()
        logger.info("CloudSyncService shutdown complete.")


cloud_sync_service = CloudSyncService()
