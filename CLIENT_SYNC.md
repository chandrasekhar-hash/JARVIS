# J.A.R.V.I.S. Client Synchronization Subsystem

This document describes the client-side synchronization architecture (`Client/sync/` and `Client/services/cloud_sync_service.py`) implemented in **Phase 8.4**.

---

## 1. Subsystem Architecture

The Client Synchronization subsystem provides local-first, offline-first operation for Desktop assistant and Mobile client instances.

```text
Client/
├── sync/
│   ├── protocol.py             # ClientSyncEnvelope & ClientMessageType DTOs
│   ├── websocket_client.py     # WebSocketSyncClient (7-state machine, heartbeat, frame loop)
│   ├── offline_store.py        # SQLite persistence driver (logs/client_sync.db)
│   ├── replay_queue.py         # Durable SQLite-backed offline operation buffer & ACK handler
│   ├── conflict_handler.py     # CRDT merge engine & manual override resolution handler
│   ├── scheduler.py            # IntelligentSyncScheduler managing trigger-based sync
│   ├── connection_monitor.py   # ConnectionMonitor tracking state, quality score, listeners
│   ├── sync_metrics.py         # SyncMetricsCollector tracking telemetry & payload bytes
│   └── sync_manager.py         # Unified ClientSyncManager entrypoint
│
└── services/
    └── cloud_sync_service.py   # High-level API for Desktop backend & Mobile bridges
```

---

## 2. Key Reliability Architecture Features

1. **Durable Operation IDs & ACK Semantics**:
   - Every local mutation generates a unique operation ID (`op_id`).
   - Mutations are persisted to the `client_pending_ops` SQLite table immediately.
   - Operations are removed from SQLite **only** upon receiving a matching `ACK` frame from the Cloud Gateway.

2. **Explicit Connection State Machine**:
   - 7 deterministic states: `DISCONNECTED` → `CONNECTING` → `AUTHENTICATING` → `SYNCHRONIZING` → `CONNECTED` → `RECONNECTING` → `ERROR`.

3. **Heartbeat & Liveness Detection**:
   - Client sends `PING` frame every 15 seconds.
   - If server `PONG` is missing for > 45 seconds, socket is marked stale and reconnects automatically.

4. **Idempotent Message Deduplication**:
   - Maintains an in-memory cache of processed message UUIDs to drop duplicate frames during replay.

5. **Crash Recovery Metadata**:
   - Stream watermarks, sequence numbers, and vector clocks are persisted atomically to `client_checkpoints` table in `logs/client_sync.db`.

6. **Manual Conflict Overrides**:
   - `ConflictHandler` provides `user_override_local(conflict_id)` and `user_override_remote(conflict_id)` methods for manual resolution.

---

## 3. High-Level Integration Code Snippet

```python
from Client.services.cloud_sync_service import cloud_sync_service

# Initialize client sync service
cloud_sync_service.initialize(
    user_id="usr_114a3a065fc0422a",
    device_id="dev_29eef772b9d24eec",
    access_token="atk_...",
    refresh_token="rtk_..."
)

# Submit local settings change (Offline-first & Durable)
res = cloud_sync_service.sync_settings({"theme": "cyberpunk_dark", "sound": True})
print("Sync Dispatch Status:", res["status"])

# Force immediate background sync replay
cloud_sync_service.force_sync()

# Get status summary
status = cloud_sync_service.get_status()
print("Connection State:", status["connection"]["state"])
print("Pending Offline Ops:", status["pending_offline_ops"])
```
