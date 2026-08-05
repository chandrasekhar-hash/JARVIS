# J.A.R.V.I.S. I2.1 — API Reference Guide

## Base URL
`http://localhost:8000/api`

---

## 1. Vision & Multimodal Endpoints

### POST `/api/vision/analyze`
Main multimodal conversation and vision analysis endpoint. Routes requests internally through `MultimodalFusionService` (V8).

- **Content-Type**: `multipart/form-data`
- **Form Parameters**:
  - `prompt` (string, optional): User question or speech text.
  - `images` (file(s), required): Uploaded image files (max 5 images, max 10MB each).
  - `conversation_context` (string, optional): JSON array of prior conversation turns.
- **Response Schema (200 OK)**:
```json
{
  "status": "success",
  "text": "The button appears disabled visually.",
  "provider": "Gemini",
  "model": "gemini-2.5-flash",
  "image_count": 1,
  "task_type": "UI_ANALYSIS",
  "visual_summary": "Disabled submit button UI screenshot.",
  "metadata": {
    "task_type": "UI_ANALYSIS",
    "visual_summary": "Disabled submit button UI screenshot.",
    "target_object": null
  }
}
```

---

### POST `/api/vision/multi-image`
Dedicated multi-image comparative intelligence endpoint (V6).

- **Content-Type**: `multipart/form-data`
- **Form Parameters**:
  - `prompt` (string, optional): Comparative instruction.
  - `images` (files, required): 2 to 5 image uploads.
- **Response Schema (200 OK)**:
```json
{
  "status": "success",
  "text": "Image 1 shows the original website design. Image 2 shows the redrawn modern UI layout.",
  "provider": "Gemini",
  "model": "gemini-2.5-flash",
  "image_count": 2,
  "task_type": "UI_COMPARISON",
  "visual_summary": "Website redesign comparison.",
  "relationships": ["modified"],
  "metadata": {}
}
```

---

### POST `/api/vision/ocr`
Dedicated document OCR extraction endpoint (V4).

- **Content-Type**: `multipart/form-data`
- **Form Parameters**:
  - `images` (file, required): Image containing text, invoice, or receipt.
- **Response Schema (200 OK)**:
```json
{
  "status": "success",
  "text": "RECEIPT #4991\nTotal: $18.50",
  "has_text": true,
  "image_count": 1,
  "provider": "Gemini",
  "model": "gemini-2.5-flash",
  "cer": 0.0,
  "images": []
}
```

---

## 2. Camera Vision Session Endpoints (V7)

### POST `/api/vision/camera/session/start`
Initializes a new Camera Vision Session.
- **Response (200 OK)**: `{"status": "success", "session_id": "session_12345", "active_focus": null}`

### POST `/api/vision/camera/session/frame`
Processes an incoming frame for an active Vision Session. Evaluates 32x32 dHash + MSE scene change detection.
- **Form Parameters**: `session_id` (string), `file` (image frame), `prompt` (optional string).
- **Response (200 OK)**: `{"status": "success", "session_id": "...", "text": "...", "scene_changed": true}`

### GET `/api/vision/camera/session/status`
Returns status, active focus, and keyframe count.
- **Query Parameter**: `session_id` (string).

### POST `/api/vision/camera/session/end`
Terminates a Vision Session and purges all RAM keyframe buffers.
- **Form Parameter**: `session_id` (string).

---

## 3. System & Health Endpoints

### GET `/api/health`
System health check.
- **Response (200 OK)**: `{"status": "healthy", "service": "JARVIS Core API"}`

### GET `/api/diagnostics/system`
System diagnostics and CPU/RAM/Disk metrics.
- **Response (200 OK)**: `{"system": {"cpu_percent": 12.5, "ram_used_mb": 420.5, "disk_used_percent": 35.0}}`
