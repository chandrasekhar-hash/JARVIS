# J.A.R.V.I.S. I2.1 — System Architecture Guide

## 1. System Overview

J.A.R.V.I.S. (Just A Rather Very Intelligent System) Version I2.1 is a modular, high-performance multimodal AI assistant architecture built with FastAPI (Python) on the backend and React + Vite on the frontend. The system provides real-time voice, computer vision, document OCR, screen/IDE understanding, multi-image comparative reasoning, camera streams, and multimodal fusion.

---

## 2. Core Architecture Diagram

```
                               ┌───────────────────────────┐
                               │   React Frontend Client   │
                               │  (Terminal & Overlays)    │
                               └─────────────┬─────────────┘
                                             │ HTTP REST / Streams
                                             ▼
                               ┌───────────────────────────┐
                               │     FastAPI Router        │
                               │  (/api/vision, /api/auth) │
                               └─────────────┬─────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │  MultimodalFusionService  │
                               │           (V8)            │
                               └─────────────┬─────────────┘
                                             │
      ┌──────────────────┬───────────────────┼───────────────────┬──────────────────┐
      ▼                  ▼                   ▼                   ▼                  ▼
VisionService       OCRService      ScreenTypeDetector   MultiImageService  CameraVisionService
   (V2/V3)             (V4)                 (V5)               (V6)                (V7)
      │                  │                   │                   │                  │
      └──────────────────┴───────────────────┼───────────────────┴──────────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │   GeminiVisionProvider    │
                               │    (gemini-2.5-flash)     │
                               └───────────────────────────┘
```

---

## 3. Subsystem Overview (V1–V8)

| Version | Capability Name | Description | Key Modules |
|---|---|---|---|
| **V1** | Image Input & Ingestion | Multipart upload, byte validation, max 10MB bounds, RAM streaming | `api/vision.py`, `models.py` |
| **V2** | Real Vision Engine | Primary Gemini provider integration, zero-hallucination bounds | `providers/gemini_vision.py`, `vision_service.py` |
| **V3** | Advanced Vision Intelligence | Task classification, single-pass visual summaries, domain prompts | `task_classifier.py`, `instruction_builder.py` |
| **V4** | OCR Intelligence | Dedicated document reading, receipt & code extraction, CER metrics | `ocr/ocr_service.py`, `ocr/cer_evaluator.py` |
| **V5** | Screenshot Intelligence | Terminal, IDE, browser, dashboard classification & domain formatting | `screenshot/screen_type_detector.py` |
| **V6** | Advanced Multi-Image | Cross-image comparative reasoning, relationship tagging, G-Eval | `multi_image/multi_image_service.py` |
| **V7** | Camera Vision | Ephemeral sessions, 32x32 dHash + MSE scene change detector (<5ms) | `camera/camera_service.py`, `camera/scene_detector.py` |
| **V8** | Voice + Vision Fusion | Multimodal context, pronoun resolution, multi-signal router, clarification | `fusion/fusion_service.py`, `fusion/pronoun_resolver.py` |

---

## 4. Ephemeral Memory Management

All visual context is strictly temporary and stored in RAM (`MultimodalContextBuilder` and `VisionSessionManager`).
- Ephemeral Rolling Buffer: Maximum 5 keyframes per camera session.
- Automatic Expiration: Ephemeral contexts and camera sessions auto-purge after 300 seconds (5 minutes) of inactivity or upon session termination.
- Zero Disk Persistence: No user images or video frames are saved to disk or database tables.
