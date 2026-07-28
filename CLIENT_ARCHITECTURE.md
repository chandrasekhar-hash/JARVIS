# J.A.R.V.I.S. Client Synchronization Architecture (Phase 8.4)

Master technical specification for the client-side synchronization architecture (`Client/`) connecting desktop and mobile personal assistant instances with the J.A.R.V.I.S. Cloud Platform (`ws://localhost:8001/ws/sync`).

---

## 1. Overview & Principles

The Client Synchronization Subsystem operates strictly on an **Offline-First** philosophy. All user operations (updating settings, saving long-term memories, modifying tasks) execute against local storage immediately. When offline, changes buffer in a persistent replay queue and synchronize seamlessly once network connectivity returns.

### Core Principles
- **Local-First Execution**: Zero user actions blocked by network availability or server latency.
- **Unified Entrypoint (`ClientSyncManager`)**: Central coordinator for connection state, local caching, replay, and CRDT conflict resolution.
- **Deterministic Conflict Merging**: Domain-specific CRDT algorithms (`LWWRegister`, `ORSet`, `LWWMap`) resolve concurrent edits automatically.
- **Resilient Reconnection**: Exponential backoff reconnect strategy (`1s` → `2s` → `4s` → `8s` → max `30s`) with automatic JWT access token refresh on expiry.

---

## 2. Component Structure (`Client/`)

```text
Client/
├── sync/
│   ├── protocol.py             # ClientSyncEnvelope & ClientMessageType schemas
│   ├── websocket_client.py     # Async WebSocketSyncClient (Exponential backoff & token refresh)
│   ├── offline_store.py        # SQLite persistent store (Checkpoints, state cache)
│   ├── replay_queue.py         # Persistent offline operation buffer & sequence-ordered worker
│   ├── conflict_handler.py     # CRDT merge coordinator & ConflictReviewNotification producer
│   ├── scheduler.py            # IntelligentSyncScheduler (Triggers: startup, change, network, periodic)
│   ├── connection_monitor.py   # ConnectionMonitor (States: CONNECTED, CONNECTING, OFFLINE, SYNCHRONIZING)
│   ├── sync_metrics.py         # Client telemetry & metrics collector
│   └── sync_manager.py         # Master ClientSyncManager orchestrator
│
└── services/
    └── cloud_sync_service.py   # High-level CloudSyncService API for Desktop & Mobile clients
```

---

## 3. Sequence Flow Diagrams

### Offline Local Change & Replay Lifecycle

```mermaid
sequenceDiagram
    participant User as Assistant App / User
    participant CSS as CloudSyncService
    participant CSM as ClientSyncManager
    participant Store as OfflineStore
    participant Queue as ReplayQueue
    participant WS as WebSocketSyncClient
    participant Cloud as Cloud Gateway (Port 8001)

    User->>CSS: sync_settings({"theme": "cyberpunk"})
    CSS->>CSM: submit_local_change("settings", changes)
    CSM->>Store: save_entity_cache("settings", snapshot)
    
    alt Network OFFLINE
        CSM->>Queue: enqueue_operation(op_id, changes, seq)
        CSM-->>User: Return {"status": "queued_offline"}
    else Network CONNECTED
        CSM->>WS: send_envelope(DELTA)
        WS->>Cloud: Transmit WSS Encrypted Delta Frame
        Cloud-->>WS: ACK (stream_id)
        CSM->>Store: save_checkpoint(last_seq)
        CSM-->>User: Return {"status": "dispatched"}
    end

    note over WS, Cloud: Network Connectivity Restored
    WS->>CSM: _on_connection_state_changed("CONNECTED")
    CSM->>Queue: drain_and_sort_queue()
    CSM->>WS: Transmit Replay Operations Batch
    WS->>Cloud: Transmit Enqueued Deltas
    CSM->>Store: save_checkpoint(watermark)
```

---

## 4. Connection State Machine

```mermaid
graph TD
    OFFLINE["OFFLINE"] -->|Network Detected| CONNECTING["CONNECTING"]
    CONNECTING -->|WS Handshake Success| CONNECTED["CONNECTED"]
    CONNECTING -->|WS Auth Failure / 401| REFRESH_TOKEN["REFRESHING JWT TOKEN"]
    REFRESH_TOKEN -->|Token Renewed| CONNECTING
    REFRESH_TOKEN -->|Token Expired| ERROR["ERROR (Auth Required)"]
    CONNECTED -->|Delta Transmitting| SYNCHRONIZING["SYNCHRONIZING"]
    SYNCHRONIZING -->|Sync Complete| CONNECTED
    CONNECTED -->|Network Drop / Disconnect| OFFLINE
```

---

## 5. High-Level Service API (`CloudSyncService`)

```python
from Client.services.cloud_sync_service import cloud_sync_service

# 1. Initialize Client
cloud_sync_service.initialize(
    user_id="usr_001",
    device_id="dev_desktop_01",
    access_token="eyJ...",
    refresh_token="rtk_..."
)

# 2. Sync Local Changes
cloud_sync_service.sync_settings({"theme": "dark_mode_pro"})
cloud_sync_service.sync_memory({"fact": "User prefers Llama-3.3-70B"})
cloud_sync_service.sync_tasks({"task_id": "101", "status": "completed"})

# 3. Inspect Connection & Metrics Status
status = cloud_sync_service.get_status()
# Returns: {"connection": {"state": "CONNECTED", ...}, "pending_offline_ops": 0, ...}
```
