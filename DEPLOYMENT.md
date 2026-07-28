# J.A.R.V.I.S. Cloud Platform Deployment Guide (Phase 8.2 & 8.3)

Guide for deploying the containerized J.A.R.V.I.S. Cloud Backend API Gateway & Real-Time Synchronization Engine.

---

## 1. Cloud Architecture Overview

The Cloud subsystem (`Cloud/`) runs independently on port **8001**, preserving the local-first, offline-first execution model of the main assistant while enabling secure multi-device synchronization.

- **Cloud API Gateway & WS Engine**: FastAPI (`Cloud/main.py`) running on port 8001
- **Database**: PostgreSQL 16 (production) with SQLite automatic fallback (development)
- **Message Broker & Event Queue**: Redis 7 Streams (`jarvis.sync.events`, `jarvis.device.events`, `jarvis.telemetry.events`)
- **Payload Security**: AES-256-GCM application-layer encryption over WSS transport with zlib threshold compression (default: 1024 bytes)

---

## 2. Local Environment Setup

### Prerequisites
- Python 3.10+
- Virtual environment (`.venv`)
- Docker & Docker Compose (optional for production containerization)

### Environment Variables (`Cloud/.env`)
```ini
APP_NAME=JARVIS Cloud Platform API Gateway & Synchronization Engine
ENVIRONMENT=production
HOST=0.0.0.0
PORT=8001
SECRET_KEY=generate_random_secure_secret_key_here
JWT_SECRET=generate_random_secure_jwt_secret_key_here
DATABASE_URL=postgresql://jarvis_cloud_user:jarvis_cloud_password@localhost:5432/jarvis_cloud_db
REDIS_URL=redis://localhost:6379/0
SYNC_COMPRESSION_THRESHOLD_BYTES=1024
```

### Running Locally without Docker
```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Run Cloud FastAPI Gateway & WebSocket Server
PYTHONPATH=Cloud python3 Cloud/main.py
```

Server starts on `http://localhost:8001` (REST) and `ws://localhost:8001/ws/sync` (WebSocket Gateway).

---

## 3. Containerized Docker Deployment

### Build & Launch Containers
```bash
cd Cloud/docker
docker-compose up -d --build
```

### Check Running Containers
```bash
docker-compose ps
```

### View Live Logs
```bash
docker-compose logs -f cloud-gateway
```

---

## 4. API & WebSocket Endpoints Reference

### Health & Observability
- `GET /api/v1/health`: Basic health probe
- `GET /api/v1/ready`: Readiness probe verifying DB, WebSocket Gateway state counts, CRDT status, and stream queue depth
- `GET /api/v1/liveness`: Liveness probe
- `GET /api/v1/security/status`: Telemetry & schema version
- `GET /api/v1/metrics`: Prometheus metrics stream (includes sync message rates, latency, and CRDT conflicts)

### Real-Time WebSocket Gateway
- `WS /ws/sync?token={JWT_ACCESS_TOKEN}`: Authenticated real-time synchronization gateway

### Device Authentication & Security
- `POST /api/v1/auth/challenge`: Generate Ed25519 challenge nonce
- `POST /api/v1/auth/device-auth`: Authenticate Ed25519 signature & issue JWT tokens
- `POST /api/v1/auth/token/refresh`: Refresh JWT access token
- `POST /api/v1/auth/token/revoke`: Revoke active session

### Device Management
- `POST /api/v1/devices/register`: Register new device
- `GET /api/v1/devices/list?user_id=usr_...`: List devices for user
- `GET /api/v1/devices/{device_id}`: Lookup device details
- `PUT /api/v1/devices/{device_id}/trust`: Update trust state (`trusted`, `revoked`)
- `PUT /api/v1/devices/{device_id}/rename`: Rename device
- `DELETE /api/v1/devices/{device_id}`: Revoke device trust

---

## 5. Automated Verification & Testing Commands

```bash
# Run Phase 8.3 Automated Unit, Integration & Load Test Suite
source .venv/bin/activate
PYTHONPATH=Cloud python3 -m unittest Cloud/tests/test_websocket.py Cloud/tests/test_delta_sync.py Cloud/tests/test_crdt.py Cloud/tests/test_replay.py Cloud/tests/test_encryption.py Cloud/tests/test_load.py

# Run Phase 8.2 Regression Test Suite
PYTHONPATH=Cloud python3 -m unittest Cloud/tests/test_cloud_backend.py

# Run Full Repository Unit Tests
PYTHONPATH=Backend python3 -m unittest Backend/test_identity.py Backend/test_plugins.py Backend/test_scheduler.py

# Health & Readiness HTTP Probes
curl -s http://localhost:8001/api/v1/health
curl -s http://localhost:8001/api/v1/ready
curl -s http://localhost:8001/api/v1/metrics
```
