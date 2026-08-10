"""
J.A.R.V.I.S. Intelligence I2.2 V8 — Ephemeral Snapshot Store Manager.
Manages RAM-only snapshot storage with strict server-derived scope isolation (owner_scope_id, conversation_id, target_id),
expiry tombstones (BASELINE_EXPIRED), atomic baseline creation locking, FIFO target eviction, and TTL expiration (3600s).
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple

from intelligence.web.monitoring.models import (
    MonitoringSnapshot,
    SnapshotTombstone,
    MonitoringConfig,
    MonitorBaselineStatus,
)

logger = logging.getLogger("JARVIS_SnapshotManager")


class EphemeralSnapshotManager:
    """
    Scope-isolated in-memory snapshot store with tombstones and atomic concurrency guards.
    """

    def __init__(self):
        # Key: (owner_scope_id, conversation_id, target_id) -> List[MonitoringSnapshot]
        self._snapshots: Dict[Tuple[str, str, str], List[MonitoringSnapshot]] = {}
        # Key: (owner_scope_id, conversation_id, target_id) -> SnapshotTombstone
        self._tombstones: Dict[Tuple[str, str, str], SnapshotTombstone] = {}
        # Locks per target scope key for atomic baseline creation
        self._target_locks: Dict[Tuple[str, str, str], asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    async def get_target_lock(self, scope_key: Tuple[str, str, str]) -> asyncio.Lock:
        async with self._global_lock:
            if scope_key not in self._target_locks:
                self._target_locks[scope_key] = asyncio.Lock()
            return self._target_locks[scope_key]

    def _purge_expired_snapshots(self, scope_key: Tuple[str, str, str]) -> None:
        """
        Evicts evidence bodies for snapshots older than SNAPSHOT_TTL_SECONDS and creates tombstones.
        """
        now = time.time()
        if scope_key in self._snapshots:
            valid_snaps: List[MonitoringSnapshot] = []
            for snap in self._snapshots[scope_key]:
                if now - snap.created_timestamp > MonitoringConfig.SNAPSHOT_TTL_SECONDS:
                    # Create tombstone before discarding snapshot body
                    tombstone = SnapshotTombstone(
                        target_id=snap.target_id,
                        owner_scope_id=snap.owner_scope_id,
                        conversation_id=snap.conversation_id,
                        expired_at=now,
                        last_snapshot_id=snap.snapshot_id,
                        expiration_reason="TTL_EXPIRED",
                    )
                    self._tombstones[scope_key] = tombstone
                    logger.info(f"Snapshot '{snap.snapshot_id}' expired. Created tombstone for scope {scope_key}.")
                else:
                    valid_snaps.append(snap)

            if valid_snaps:
                self._snapshots[scope_key] = valid_snaps
            else:
                del self._snapshots[scope_key]

    def get_latest_snapshot(
        self, owner_scope_id: str, conversation_id: str, target_id: str
    ) -> Tuple[Optional[MonitoringSnapshot], MonitorBaselineStatus]:
        """
        Retrieves the latest valid snapshot or returns NO_BASELINE / BASELINE_EXPIRED status.
        """
        scope_key = (owner_scope_id or "default_owner", conversation_id or "default_conv", target_id)
        self._purge_expired_snapshots(scope_key)

        if scope_key in self._snapshots and self._snapshots[scope_key]:
            return self._snapshots[scope_key][-1], MonitorBaselineStatus.NO_CHANGE

        if scope_key in self._tombstones:
            return None, MonitorBaselineStatus.BASELINE_EXPIRED

        return None, MonitorBaselineStatus.NO_BASELINE

    def store_snapshot(
        self, snapshot: MonitoringSnapshot
    ) -> None:
        """
        Stores snapshot in RAM enforcing target limits and snapshot limits.
        """
        scope_key = (snapshot.owner_scope_id, snapshot.conversation_id, snapshot.target_id)
        self._purge_expired_snapshots(scope_key)

        if scope_key not in self._snapshots:
            self._snapshots[scope_key] = []

        snaps = self._snapshots[scope_key]
        if len(snaps) > 0:
            snapshot.previous_snapshot_id = snaps[-1].snapshot_id

        snaps.append(snapshot)

        # Enforce MAX_SNAPSHOTS_PER_TARGET bound (FIFO eviction)
        if len(snaps) > MonitoringConfig.MAX_SNAPSHOTS_PER_TARGET:
            snaps.pop(0)

        # Clear any existing tombstone on fresh baseline creation
        if scope_key in self._tombstones:
            del self._tombstones[scope_key]

    def clear_all(self) -> None:
        """
        Clears all in-memory snapshot state.
        """
        self._snapshots.clear()
        self._tombstones.clear()
        self._target_locks.clear()


snapshot_manager = EphemeralSnapshotManager()
