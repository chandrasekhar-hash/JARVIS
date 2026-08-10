"""
Ephemeral Bounded TemporalSnapshotStore for J.A.R.V.I.S. I2.2 V4.
Manages ephemeral, RAM-only TemporalSnapshot instances for since-last-check diffing.
Webpage bodies are NEVER stored. Strict 1-hour TTL and bounded snapshots per conversation.
"""

import time
import asyncio
from typing import Dict, List, Optional, Tuple, Set
from intelligence.web.temporal.models import (
    TemporalSnapshot,
    TemporalDiffStatus,
    NewsEvent,
    TemporalClaim
)

SNAPSHOT_TTL_SECONDS = 3600  # 1 hour TTL
MAX_SNAPSHOTS_PER_CONVERSATION = 5


class TemporalSnapshotStore:
    """Async-safe, bounded ephemeral RAM snapshot store for since-last-check diffing."""

    def __init__(self):
        self._store: Dict[str, List[TemporalSnapshot]] = {}
        self._lock = asyncio.Lock()

    async def get_latest_snapshot(self, conversation_id: str) -> Optional[TemporalSnapshot]:
        """
        Retrieves the latest valid snapshot for a conversation.
        Evicts expired snapshots based on SNAPSHOT_TTL_SECONDS.
        """
        async with self._lock:
            if conversation_id not in self._store:
                return None

            now = time.time()
            snapshots = self._store[conversation_id]

            # Filter out expired snapshots
            valid_snapshots = [s for s in snapshots if (now - s.snapshot_created_at) < SNAPSHOT_TTL_SECONDS]
            self._store[conversation_id] = valid_snapshots

            if not valid_snapshots:
                return None

            return valid_snapshots[-1]

    async def save_snapshot(
        self,
        conversation_id: str,
        topic_fingerprint: str,
        events: List[NewsEvent],
        claims: List[TemporalClaim],
        canonical_urls: List[str],
        source_ids: List[str]
    ) -> TemporalSnapshot:
        """
        Saves structured metadata-only snapshot.
        Webpage bodies are NEVER stored.
        Enforces MAX_SNAPSHOTS_PER_CONVERSATION limit.
        """
        async with self._lock:
            now = time.time()
            event_fps = {f"{e.event_id}:{e.title[:40]}" for e in events}
            claim_fps = {f"{c.claim_id}:{c.statement[:40]}" for c in claims}

            snapshot = TemporalSnapshot(
                snapshot_id=f"snap_{int(now * 1000)}",
                conversation_id=conversation_id,
                topic_fingerprint=topic_fingerprint,
                event_fingerprints=event_fps,
                claim_fingerprints=claim_fps,
                canonical_urls=set(canonical_urls),
                source_ids=set(source_ids),
                published_at=events[0].first_published_at if events else None,
                updated_at=events[0].latest_update_at if events else None,
                event_time=events[0].event_time if events else None,
                retrieved_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
                snapshot_created_at=now
            )

            if conversation_id not in self._store:
                self._store[conversation_id] = []

            # Filter expired and append
            valid = [s for s in self._store[conversation_id] if (now - s.snapshot_created_at) < SNAPSHOT_TTL_SECONDS]
            valid.append(snapshot)

            # Bounded memory: keep latest N snapshots
            if len(valid) > MAX_SNAPSHOTS_PER_CONVERSATION:
                valid = valid[-MAX_SNAPSHOTS_PER_CONVERSATION:]

            self._store[conversation_id] = valid
            return snapshot

    def compute_diff_status(
        self,
        new_urls: List[str],
        new_events: List[NewsEvent],
        previous_snapshot: Optional[TemporalSnapshot]
    ) -> Tuple[TemporalDiffStatus, bool]:
        """
        Computes explicit TemporalDiffStatus against previous metadata snapshot:
        NEW, UPDATED, UNCHANGED, REMOVED, CORRECTED, UNKNOWN.
        Returns (TemporalDiffStatus, has_prior_baseline).
        """
        if previous_snapshot is None:
            return TemporalDiffStatus.NEW, False

        prev_urls = previous_snapshot.canonical_urls
        new_url_set = set(new_urls)

        # 1. Check for removed URLs/sources
        removed_urls = prev_urls - new_url_set
        if removed_urls and not new_url_set:
            return TemporalDiffStatus.REMOVED, True

        # 2. Check for corrections in event categories
        has_correction = any(e.update_category.value == "CORRECTION" for e in new_events)
        if has_correction:
            return TemporalDiffStatus.CORRECTED, True

        # 3. Check for new URLs or updated events
        added_urls = new_url_set - prev_urls
        if added_urls:
            return TemporalDiffStatus.NEW, True

        # 4. Check for updated event fingerprints
        new_fps = {f"{e.event_id}:{e.title[:40]}" for e in new_events}
        if new_fps != previous_snapshot.event_fingerprints:
            return TemporalDiffStatus.UPDATED, True

        return TemporalDiffStatus.UNCHANGED, True


temporal_snapshot_store = TemporalSnapshotStore()
