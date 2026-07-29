"""
Memory Settings & Privacy Controls Manager for Phase P1.2 (Memory & Personalization).
Handles privacy toggles, full memory exports/imports, and memory clearing.
"""
import time
import uuid
import json
import logging
from typing import Optional, Dict, Any, Tuple, List

from .memory_models import (
    Memory,
    MemorySettings,
    MemoryStatus,
    PersonalizationProfile,
)
from .memory_interfaces import (
    IMemorySettingsRepository,
    IMemoryRepository,
    IPersonalizationRepository,
)

logger = logging.getLogger("JARVIS_MemorySettingsManager")


class MemorySettingsManager:
    """
    Privacy Controls and Memory Management domain service.
    Orchestrates user privacy toggles, export, import, and clearing.
    """

    def __init__(
        self,
        settings_repository: IMemorySettingsRepository,
        memory_repository: IMemoryRepository,
        personalization_repository: Optional[IPersonalizationRepository] = None,
    ):
        self.settings_repo = settings_repository
        self.memory_repo = memory_repository
        self.personalization_repo = personalization_repository

    def get_settings(self, user_id: str) -> MemorySettings:
        """Retrieves user memory settings."""
        return self.settings_repo.get_settings(user_id)

    def update_settings(
        self,
        user_id: str,
        memory_enabled: Optional[bool] = None,
        auto_summarize: Optional[bool] = None,
        max_working_memory_items: Optional[int] = None,
        retention_days: Optional[int] = None,
        privacy_opt_out: Optional[bool] = None,
    ) -> MemorySettings:
        """Updates privacy toggles and retention parameters."""
        settings = self.settings_repo.get_settings(user_id)

        if memory_enabled is not None:
            settings.memory_enabled = memory_enabled
        if auto_summarize is not None:
            settings.auto_summarize = auto_summarize
        if max_working_memory_items is not None:
            settings.max_working_memory_items = max_working_memory_items
        if retention_days is not None:
            settings.retention_days = retention_days
        if privacy_opt_out is not None:
            settings.privacy_opt_out = privacy_opt_out

        settings.updated_at = time.time()
        return self.settings_repo.save_settings(settings)

    def export_memories(self, user_id: str) -> Dict[str, Any]:
        """
        Exports all active and archived user memories, personalization profile,
        and settings to a structured dictionary format for backup/portability.
        """
        memories = self.memory_repo.list_memories(user_id=user_id, status=None, limit=1000)
        settings = self.get_settings(user_id)

        personalization = None
        if self.personalization_repo:
            profile = self.personalization_repo.get_profile(user_id)
            if profile:
                personalization = profile.to_dict()

        return {
            "version": "1.0",
            "exported_at": time.time(),
            "user_id": user_id,
            "settings": settings.to_dict(),
            "personalization": personalization,
            "memories": [m.to_dict() for m in memories],
        }

    def import_memories(self, user_id: str, import_data: Dict[str, Any]) -> Tuple[int, str]:
        """
        Imports memories from an exported JSON structure into the user's memory store.
        Returns: (imported_count, message)
        """
        if not import_data or "memories" not in import_data:
            return 0, "Invalid import data payload."

        imported_count = 0
        raw_memories = import_data.get("memories", [])

        for item in raw_memories:
            try:
                item_copy = dict(item)
                # Override user_id and generate fresh memory_id for strict security isolation
                item_copy["user_id"] = user_id
                item_copy["memory_id"] = f"mem_{str(uuid.uuid4())}"
                mem = Memory.from_dict(item_copy)
                self.memory_repo.create_memory(mem)
                imported_count += 1
            except Exception as e:
                logger.warning(f"[MemorySettingsManager] Failed to import memory item: {e}")

        logger.info(f"[MemorySettingsManager] Successfully imported {imported_count} memories for user '{user_id}'.")
        return imported_count, f"Successfully imported {imported_count} memories."

    def clear_all_memories(self, user_id: str) -> int:
        """Clears all memory records for a user ID."""
        cleared = self.memory_repo.clear_user_memories(user_id)
        logger.info(f"[MemorySettingsManager] Cleared {cleared} memories for user '{user_id}'.")
        return cleared
