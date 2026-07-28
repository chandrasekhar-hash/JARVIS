# J.A.R.V.I.S. API Reference

This document describes the FastAPI REST endpoints and SSE streams exposed by the JARVIS Core Backend.

---

## 1. System Health & Observability Endpoints

### Health Check
* **Endpoint:** `GET /health`
* **Purpose:** Minimal probe verifying the FastAPI server process is running.
* **Response (200 OK):**
  ```json
  {"status": "healthy"}
  ```

### Diagnostics Readiness
* **Endpoint:** `GET /ready`
* **Purpose:** Performs diagnostic checks on external dependencies (Groq Connectivity, Edge TTS, registry tools, filesystem, and configuration).
* **Response (200 OK or 503 Service Unavailable):**
  ```json
  {
    "ready": true,
    "details": {
      "configuration": "valid",
      "tool_registry": "active (13 tools)",
      "filesystem": "accessible",
      "groq_connectivity": "connected",
      "edge_tts": "available"
    }
  }
  ```

### Performance Metrics
* **Endpoint:** `GET /metrics`
* **Purpose:** Exposes CPU, RAM, active task lists, and sliding metrics stats (Last 1m, 5m, Session, and Startup).
* **Response (200 OK):**
  ```json
  {
    "llm_latency": {
      "1m": {"avg": 0.452, "p95": 0.452, "max": 0.452, "count": 1},
      "5m": {"avg": 0.452, "p95": 0.452, "max": 0.452, "count": 1},
      "session": {"avg": 0.452, "p95": 0.452, "max": 0.452, "count": 1}
    },
    "counts": {
      "llm_requests": 1,
      "tts_requests": 1,
      "browser_operations": 0,
      "file_operations": 0,
      "active_conversations": 0,
      "active_tool_executions": 0
    },
    "system": {
      "cpu_percent": 12.5,
      "ram_mb": 65.34
    },
    "active_tasks": []
  }
  ```

---

## 2. Conversational API

### Voices List
* **Endpoint:** `GET /api/voices`
* **Purpose:** Populates the frontend configuration selectors.
* **Response (200 OK):**
  ```json
  {
    "engines": ["edge"],
    "languages": ["English", "Hindi", "Hinglish", "Telugu", ...],
    "genders": ["Female", "Male"]
  }
  ```

### Chat SSE Stream
* **Endpoint:** `POST /api/chat`
* **Purpose:** Receives user transcripts and pipes responses via Server-Sent Events (SSE) streaming text tokens and parallel TTS audio URLs.
* **Payload:**
  ```json
  {
    "message": "Open YouTube",
    "voice": "female",
    "language": "english",
    "tts_language": ""
  }
  ```
* **SSE Yield Formats:**
  - Text Token: `data: {"type": "text", "content": "Open"}`
  - Audio URL segment: `data: {"type": "audio_url", "url": "/api/audio/uuid-123", "text": "Opening YouTube"}`
  - Errors: `data: {"type": "error", "content": "Details"}`

---

## 4. Local Plugin Framework REST Endpoints (Phase 6)

### List Installed Plugins
* **Endpoint:** `GET /api/plugins`
* **Purpose:** Returns list of all locally discovered plugins, manifests, permissions, and tool statuses.

### Plugin Details
* **Endpoint:** `GET /api/plugins/{plugin_id}`
* **Purpose:** Returns manifest metadata and health status for a specific plugin ID.

### Enable Plugin
* **Endpoint:** `POST /api/plugins/{plugin_id}/enable`
* **Purpose:** Enables plugin, registers its tools in `ToolRegistry`, and sets state to running.

### Disable Plugin
* **Endpoint:** `POST /api/plugins/{plugin_id}/disable`
* **Purpose:** Disables plugin, unregisters its tools from `ToolRegistry`, and sets state to disabled.

### Reload Plugin
* **Endpoint:** `POST /api/plugins/{plugin_id}/reload`
* **Purpose:** Dynamically unloads and re-imports plugin entrypoint module from `Backend/plugins_installed/{id}/` without backend restart.

### Plugin Health Check
* **Endpoint:** `GET /api/plugins/{plugin_id}/health`
* **Purpose:** Verifies entrypoint file existence, status integrity, and health boolean.
