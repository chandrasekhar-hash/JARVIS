# J.A.R.V.I.S. Multi-Device Synchronization User & Developer Guide

Welcome to the **J.A.R.V.I.S. Multi-Device Synchronization Guide** (Phase 8.4). This document explains how multi-device synchronization works across Desktop and Mobile assistant instances, connection status indicators, offline editing, and troubleshooting.

---

## 1. Key Features

- **Offline-First Synchronization**: Work completely offline. Changes to settings, memories, and tasks save locally instantly and sync automatically when internet access is restored.
- **Conflict-Free State Resolution**: Domain-specific CRDT algorithms automatically merge changes from multiple devices without corrupting data or prompting for manual intervention.
- **Application-Layer AES-256-GCM Payload Protection**: All synchronized payloads are encrypted over WSS transport.
- **Transparent Reconnection**: Automatic exponential backoff reconnects and seamless JWT token refresh.

---

## 2. Connection Status Indicators

The assistant interface displays real-time connection telemetry:

| Indicator State | Description | Action Needed |
| :---: | :--- | :--- |
| **🟢 CONNECTED** | Connected to Cloud Platform. Data is fully synchronized. | None. Operating normally. |
| **🟡 CONNECTING** | Attempting WebSocket connection or renewing access token. | Wait a few seconds while connection establishes. |
| **🔵 SYNCHRONIZING** | Dispatched delta update or replaying offline operations. | None. Sync in progress. |
| **⚪ OFFLINE** | No network connection detected. Operating from local cache. | Local changes are saved in offline replay buffer. |
| **🔴 ERROR** | Authentication or token refresh failed. | Re-authenticate device via `/api/v1/auth/device-auth`. |

---

## 3. Developer Integration Guide

To integrate synchronization into any client application or mobile companion bridge:

```python
from Client.services.cloud_sync_service import cloud_sync_service

# Step 1: Initialize service on startup
cloud_sync_service.initialize(
    user_id="usr_12345",
    device_id="dev_macbook_pro",
    access_token="<JWT_ACCESS_TOKEN>",
    refresh_token="<JWT_REFRESH_TOKEN>"
)

# Step 2: Trigger synchronization on local data edits
cloud_sync_service.sync_settings({"theme": "cyberpunk_dark", "volume": 80})

# Step 3: Trigger manual sync if requested by user
result = cloud_sync_service.force_sync()
print(f"Force sync triggered: {result}")

# Step 4: Check connection telemetry
status = cloud_sync_service.get_status()
print(f"Status: {status['connection']['state']} | Pending Offline Ops: {status['pending_offline_ops']}")
```

---

## 4. Troubleshooting Guide

### Issue: Device Status shows `OFFLINE` while internet connection is active
- **Cause**: Cloud Gateway container on port 8001 may not be running.
- **Solution**: Check if Cloud backend container is running via `docker-compose ps` or start locally using `PYTHONPATH=Cloud python3 Cloud/main.py`.

### Issue: Token Refresh Fails (`ERROR` state)
- **Cause**: 30-day refresh token expired or device trust state was revoked.
- **Solution**: Execute Ed25519 challenge-response re-authentication via `POST /api/v1/auth/challenge` and `POST /api/v1/auth/device-auth`.

### Issue: Pending Offline Operations Count Not Decreasing
- **Cause**: WebSocket connection in `CONNECTING` retry loop due to network jitter.
- **Solution**: Use `cloud_sync_service.force_sync()` to trigger explicit queue drain when connectivity stabilizes.
