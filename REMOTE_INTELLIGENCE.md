# J.A.R.V.I.S. Remote Intelligence Subsystem Architecture

This document details the **Remote Intelligence Subsystem (`Cloud/intelligence/` & `Cloud/services/`)** implemented in **Phase 8.5**.

---

## 1. Overview & Objectives

Phase 8.5 completes the **Phase 8 Cloud & Multi-Device Architecture** by providing:
- **Remote LLM Inference Offloading**: Delegates heavy 70B LLM reasoning queries and tool planning from hardware-constrained local clients (e.g. mobile apps, low-spec laptops) to Cloud LLM runtimes (Groq, Gemini, OpenRouter).
- **Provider Abstraction & Circuit Breakers**: Independent circuit breakers (`CLOSED` → `OPEN` → `HALF_OPEN`) preventing cascading outages.
- **Cross-Device Context Sharing Mesh**: Aggregates active device context snapshots (desktop screen, active app, mobile location, user intent) with versioning, confidence scores, and TTL expirations.
- **Cryptographic Remote Execution Trust Model**: Enforces Zero-Trust remote agent command execution with Ed25519 payload signatures, nonce replay protection, and capability-based authorization.
- **Distributed Job Orchestration**: `JobOrchestrator` managing job state transitions (`QUEUED` → `RUNNING` → `COMPLETED` → `FAILED` → `CANCELLED`), priority scheduling, retries, and timeouts.
- **Cloud Scheduler Relay**: Automatically executes background autonomous tasks in the Cloud when the primary scheduling device goes offline.
- **Proactive Multi-Device Notification Mesh**: Broadcasts real-time alerts and task outputs to active WebSocket connection channels.

---

## 2. Directory Layout & Module Structure

```text
Cloud/
├── alembic/
│   └── versions/
│       └── a11y2c3d4e5f6_add_phase8_5_remote_intelligence_tables.py
│
├── models/
│   └── orm.py                          # CloudContextSnapshotModel, CloudNotificationModel, CloudRemoteJobModel
│
├── intelligence/
│   ├── base_provider.py                # BaseRemoteInferenceProvider abstract interface
│   ├── groq_provider.py                # Groq provider implementation
│   ├── gemini_provider.py              # Gemini provider implementation
│   ├── openrouter_provider.py          # OpenRouter provider implementation
│   ├── circuit_breaker.py              # Provider CircuitBreaker pattern
│   ├── offloader.py                    # RemoteInferenceOffloader router & stream engine
│   ├── context_mesh.py                 # ContextSnapshot & CrossDeviceContextProvider
│   └── remote_agent.py                 # Cryptographic Ed25519 payload verification
│
├── services/
│   ├── presence_service.py             # Centralized PresenceService (capabilities & workload)
│   ├── context_mesh_service.py         # ContextMeshService storage & TTL manager
│   ├── job_orchestrator.py             # JobOrchestrator & state machine
│   ├── cloud_scheduler_relay.py        # CloudSchedulerRelay task takeover engine
│   └── notification_service.py         # NotificationMeshService broadcast engine
│
└── routes/
    └── intelligence_routes.py          # FastAPI REST & SSE endpoints
```

---

## 3. Key REST API Endpoints

- `POST /api/v1/intelligence/inference`: Synchronous remote LLM inference.
- `POST /api/v1/intelligence/inference/stream`: SSE token streaming remote LLM inference.
- `POST /api/v1/intelligence/context/snapshot`: Submit device context snapshot.
- `GET /api/v1/intelligence/context`: Get aggregated cross-device prompt context header.
- `POST /api/v1/intelligence/agent/execute`: Execute cryptographically signed remote agent command.
- `POST /api/v1/intelligence/presence`: Update device status, capabilities, and workload score.
- `GET /api/v1/intelligence/notifications`: Retrieve unread notifications.
- `GET /api/v1/intelligence/circuit_status`: Query health status of provider circuit breakers.

---

## 4. Cryptographic Security Model

Remote command execution enforces Zero-Trust cryptographic verification:

1. **Payload Signing**: The originating device signs the canonical JSON command payload (containing `action`, `timestamp`, `nonce`, and `capabilities`) using its private Ed25519 key.
2. **Replay Protection**: The Cloud Gateway checks the `nonce` against an in-memory replay cache and validates `timestamp` within a 300-second window.
3. **Signature Verification**: Verified against the originating device's public key registered in `cloud_devices`.
4. **Capability Check**: Ensures the command payload specifies required capabilities (e.g. `desktop_execution`).
