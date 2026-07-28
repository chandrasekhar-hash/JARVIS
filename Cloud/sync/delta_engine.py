import time
import json
import logging
from typing import Dict, Any, Tuple, Optional
from sync.crdt import crdt_engine
from sync.encryption import payload_encryptor, COMPRESSION_THRESHOLD_BYTES

logger = logging.getLogger("JARVIS_Cloud_Delta")


class DeltaEngine:
    """
    DeltaEngine generating state delta patches, tracking version numbers, and maintaining checkpoints.
    Never sends full state when an incremental patch is sufficient.
    """

    def __init__(self):
        self.entity_versions: Dict[str, int] = {
            "settings": 1,
            "memory": 1,
            "tasks": 1,
            "preferences": 1,
            "conversation_metadata": 1
        }

    def increment_version(self, entity_type: str) -> int:
        if entity_type in self.entity_versions:
            self.entity_versions[entity_type] += 1
            return self.entity_versions[entity_type]
        self.entity_versions[entity_type] = 1
        return 1

    def create_delta_patch(
        self,
        user_id: str,
        device_id: str,
        entity_type: str,
        changes: Dict[str, Any],
        encrypt: bool = True
    ) -> Dict[str, Any]:
        version = self.increment_version(entity_type)
        raw_patch = {
            "type": "delta",
            "entity_type": entity_type,
            "version": version,
            "changes": changes,
            "timestamp": time.time()
        }

        if encrypt:
            encrypted_payload = payload_encryptor.encrypt(raw_patch)
            return {
                "user_id": user_id,
                "device_id": device_id,
                "version": version,
                "encrypted": True,
                "payload": encrypted_payload
            }

        return {
            "user_id": user_id,
            "device_id": device_id,
            "version": version,
            "encrypted": False,
            "payload": raw_patch
        }

    def apply_delta_patch(self, delta_wrapper: Dict[str, Any], device_id: str) -> Tuple[bool, int]:
        """
        Decrypts (if encrypted) and merges delta patch into CRDT engine.
        Returns (success_boolean, conflicts_resolved).
        """
        try:
            if delta_wrapper.get("encrypted", False):
                patch = payload_encryptor.decrypt(delta_wrapper["payload"])
            else:
                patch = delta_wrapper["payload"]

            entity_type = patch.get("entity_type", "settings")
            changes = patch.get("changes", {})
            timestamp = patch.get("timestamp", time.time())

            conflicts_resolved = 0
            if entity_type == "settings":
                conflicts_resolved = crdt_engine.merge_settings(changes, timestamp, device_id)
            elif entity_type == "memory":
                conflicts_resolved = crdt_engine.merge_memory(changes, timestamp, device_id)
            elif entity_type == "tasks":
                crdt_engine.merge_tasks(changes)

            return True, conflicts_resolved
        except Exception as e:
            logger.error(f"Failed to apply delta patch: {e}")
            return False, 0


delta_engine = DeltaEngine()
