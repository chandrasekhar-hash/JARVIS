# J.A.R.V.I.S. API Reference Manual

Master specification of REST and WebSocket endpoints across the J.A.R.V.I.S. Platform.

---

## 1. Intent Classifier & Direct Tools

### Direct Execution
* **Endpoint:** `POST /api/chat`
* **Protocol:** HTTP REST / SSE Stream
* **Purpose:** Process natural language commands through intent classification and tool execution.

---

## 2. Long-Term Memory API (Phase 4)

### Store Observation
* **Endpoint:** `POST /api/memory/store`
* **Payload:** `{"content": "...", "category": "user_preference", "confidence": 0.95}`
* **Purpose:** Stores an observation into the 3-Layer Memory Engine.

### Query Memory
* **Endpoint:** `POST /api/memory/query`
* **Payload:** `{"query": "...", "top_k": 5}`
* **Purpose:** Retrieves relevant memories based on vector similarity and 5-factor ranking.

---

## 3. Persistent Autonomous Scheduler API (Phase 7)

### Create Scheduled Job
* **Endpoint:** `POST /api/scheduler/jobs`
* **Payload:** `{"name": "...", "expression": "Every morning at 8", "task_type": "memory_cleanup"}`
* **Purpose:** Schedules an autonomous task.

### List Jobs
* **Endpoint:** `GET /api/scheduler/jobs`
* **Purpose:** Returns list of active scheduled jobs.

---

## 4. Local Identity & Security API (Phase 8.1 - Port 8000)

### Security Status
* **Endpoint:** `GET /api/security/status`
* **Purpose:** Returns local user identity and device trust state.

### Device Trust Update
* **Endpoint:** `POST /api/device/trust`
* **Payload:** `{"device_id": "...", "trust_state": "TRUSTED"}`
* **Purpose:** Modifies local device trust level.

---

## 5. Cloud Backend Infrastructure REST API (Phase 8.2 - Port 8001)

### Authentication Challenge
* **Endpoint:** `POST /api/v1/auth/challenge`
* **Payload:** `{"device_id": "dev_..."}`
* **Response:** `{"challenge": {"nonce": "...", "expires_at": ...}}`
* **Purpose:** Initiates Ed25519 challenge-response sequence.

### Device Authentication
* **Endpoint:** `POST /api/v1/auth/device-auth`
* **Payload:** `{"device_id": "dev_...", "nonce": "...", "signature_b64": "..."}`
* **Response:** `{"tokens": {"access_token": "...", "refresh_token": "..."}}`
* **Purpose:** Validates Ed25519 signature and returns JWT access and refresh tokens.

### Token Refresh
* **Endpoint:** `POST /api/v1/auth/token/refresh`
* **Payload:** `{"refresh_token": "..."}`
* **Response:** `{"tokens": {"access_token": "...", "refresh_token": "..."}}`
* **Purpose:** Exchanges refresh token for new access token.

### Token Revocation
* **Endpoint:** `POST /api/v1/auth/token/revoke`
* **Payload:** `{"session_id": "ses_..."}`
* **Purpose:** Revokes a session token.

### Device Registration
* **Endpoint:** `POST /api/v1/devices/register`
* **Payload:** `{"device_name": "...", "platform": "...", "architecture": "...", "os_version": "...", "public_key": "..."}`
* **Purpose:** Registers a new device with Ed25519 public key.

### Device List
* **Endpoint:** `GET /api/v1/devices/list?user_id=usr_...`
* **Purpose:** Lists all devices registered to a cloud user.

### Update Device Trust
* **Endpoint:** `PUT /api/v1/devices/{device_id}/trust`
* **Payload:** `{"trust_state": "trusted" | "revoked"}`
* **Purpose:** Updates cloud device trust state.

### Cloud Observability & Probes
* **Endpoint:** `GET /api/v1/health`: Cloud API Gateway health probe.
* **Endpoint:** `GET /api/v1/ready`: Cloud readiness probe including WebSocket state counts, CRDT status, and stream queue depth.
* **Endpoint:** `GET /api/v1/liveness`: Cloud liveness probe.
* **Endpoint:** `GET /api/v1/security/status`: Detailed cloud security telemetry.
* **Endpoint:** `GET /api/v1/metrics`: Prometheus metrics stream including sync connection, message rate, latency, and conflict counters.

---

## 6. Cloud Synchronization Gateway WebSocket API (Phase 8.3 - Port 8001)

### WebSocket Real-Time Synchronization Endpoint
* **Endpoint:** `ws://localhost:8001/ws/sync?token={JWT_ACCESS_TOKEN}`
* **Protocol:** Bidirectional JSON envelopes (`SyncMessageEnvelope`) over WebSocket transport.
* **Supported Message Types:** `AUTH`, `AUTH_OK`, `SYNC_REQUEST`, `SYNC_RESPONSE`, `DELTA`, `ACK`, `PING`, `PONG`, `DEVICE_JOIN`, `DEVICE_LEAVE`, `ERROR`.
* **Reserved Future Message Types:** `PLUGIN_SYNC`, `VOICE_SYNC`, `FILE_SYNC`, `MODEL_SYNC`, `NOTIFICATION`.
* **Payload Encryption:** AES-256-GCM application-layer payload encryption with threshold compression (>1 KB compressed with zlib before encryption).
* **Connection Lifecycle States:** `CONNECTING` → `AUTHENTICATING` → `SYNCHRONIZING` → `ACTIVE` → `IDLE` → `RECONNECTING` → `DISCONNECTED`.

---

## 7. Client Synchronization Service API (Phase 8.4 - `Client/services/cloud_sync_service.py`)

### `cloud_sync_service.initialize(user_id, device_id, access_token, refresh_token)`
* **Purpose:** Initializes client synchronization manager, configures credentials, and starts `IntelligentSyncScheduler`.

### `cloud_sync_service.sync_settings(settings_dict)`
* **Purpose:** Dispatches settings change delta. Dispatches over WebSocket if online, or queues in `ReplayQueue` if offline.

### `cloud_sync_service.sync_memory(memory_dict)`
* **Purpose:** Dispatches long-term memory facts update delta with CRDT merge resolution.

### `cloud_sync_service.sync_tasks(tasks_dict)`
* **Purpose:** Dispatches autonomous task state update delta.

### `cloud_sync_service.force_sync()`
* **Purpose:** Triggers immediate manual sync attempt and drains pending offline operation queue.

### `cloud_sync_service.get_status()`
* **Purpose:** Returns status payload containing connection state (`CONNECTED`, `CONNECTING`, `OFFLINE`, `SYNCHRONIZING`, `ERROR`), quality score, pending offline change count, and telemetry metrics summary.
