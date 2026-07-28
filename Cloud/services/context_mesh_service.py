import time
import uuid
import logging
from typing import Dict, Any, List, Optional
from Cloud.intelligence.context_mesh import ContextSnapshot, CrossDeviceContextProvider

logger = logging.getLogger("JARVIS_ContextMeshService")


class ContextMeshService:
    """
    ContextMeshService managing ingestion, versioning, TTL expiry, and query
    of active cross-device context snapshots.
    """

    def __init__(self):
        # user_id -> List[ContextSnapshot]
        self._snapshots: Dict[str, List[ContextSnapshot]] = {}

    def submit_snapshot(
        self,
        user_id: str,
        device_id: str,
        context_type: str,
        data: Dict[str, Any],
        ttl_seconds: float = 300.0,
        confidence: float = 1.0
    ) -> ContextSnapshot:
        user_snaps = self._snapshots.setdefault(user_id, [])

        # Check existing version for device_id + context_type
        existing_version = 0
        for s in user_snaps:
            if s.device_id == device_id and s.context_type == context_type:
                existing_version = max(existing_version, s.version)

        snap = ContextSnapshot(
            snapshot_id=f"snp_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            device_id=device_id,
            context_type=context_type,
            version=existing_version + 1,
            confidence=confidence,
            data=data,
            expires_at=time.time() + ttl_seconds
        )
        user_snaps.append(snap)
        logger.info(f"Ingested context snapshot '{snap.snapshot_id}' (v{snap.version}) for user '{user_id}' from device '{device_id}'")
        return snap

    def get_valid_snapshots_for_user(self, user_id: str) -> List[ContextSnapshot]:
        snaps = self._snapshots.get(user_id, [])
        valid = [s for s in snaps if not s.is_expired()]
        self._snapshots[user_id] = valid
        return valid

    def get_formatted_context_header(self, user_id: str) -> str:
        valid_snaps = self.get_valid_snapshots_for_user(user_id)
        return CrossDeviceContextProvider.format_context_prompt_header(valid_snaps)


context_mesh_service = ContextMeshService()
