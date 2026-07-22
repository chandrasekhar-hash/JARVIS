# Phase 3 Changelog — JARVIS Vision & Multimodal Intelligence

All notable changes introduced during **Phase 3 Development & Vision Architecture Consolidation**.

---

## Summary of Release (v3.0.0)

Phase 3 introduces Vision as a first-class capability of the JARVIS platform. JARVIS can now observe desktop screens, extract text via OCR, understand UI control bounding boxes, classify active applications and user workflows, detect visual screen changes, and inject structured visual context into the Brain.

---

## Completed Milestones

### ✅ Milestone 3.1 — Screen Capture Subsystem (`Backend/vision/capture/`)
- Multi-monitor enumeration & coordinate bounds detection (`monitor_manager`).
- Pixel capture engine with Win32 GDI BitBlt, Pillow `ImageGrab`, and `PyAutoGUI` fallbacks (`capture_engine`).
- Session-based capture permission governance (`ALLOW_ONCE`, `ALWAYS_ALLOW`, `DENY`).
- Vision Service Lifecycle Controller (`start_vision`, `stop_vision`, `pause_vision`, `resume_vision`).

### ✅ Milestone 3.2 — OCR & Spatial Text Mapping (`Backend/vision/analysis/ocr.py`, `preprocess.py`, `text_mapper.py`)
- Preprocessing pipeline (grayscale conversion, contrast enhancement, sharpening, resolution scaling).
- Spatial reading order mapper preserving top-to-bottom, left-to-right reading order, line grouping (`tolerance <= 12px`), and paragraph grouping (`gap > 28px`).
- OCR Engine supporting EasyOCR, PyTesseract, and native desktop layout fallback.

### ✅ Milestone 3.3 — UI Understanding & Element Grounding (`Backend/vision/analysis/ui.py`, `grounding.py`)
- Support for 17 UI control types (`BUTTON`, `INPUT`, `PASSWORD`, `DROPDOWN`, `CHECKBOX`, `RADIO`, `LINK`, `MENU`, `TOOLBAR`, `TAB`, `WINDOW`, `DIALOG`, `ICON`, `IMAGE`, `SCROLLBAR`, `STATUS_BAR`, `NAV_PANEL`).
- Spatial coordinate element grounding (`element_grounding_engine.ground_target`) mapping natural language targets to `(center_x, center_y)` click coordinates.
- Active window title and process context integration.

### ✅ Milestone 3.4 — Scene Understanding & Vision Context (`Backend/vision/analysis/scene.py`, `context/`)
- Classification of 9 application categories and observable user workflows.
- Visual change detector (`change_detector`) tracking `APP_SWITCHED`, `WINDOW_OPENED`, `WINDOW_CLOSED`, `DIALOG_APPEARED`, `NOTIFICATION_APPEARED`, `SCREEN_UNCHANGED`.
- Short-term visual memory context manager (`visual_context_manager`) maintaining frame history timeline.

### ✅ Milestone 3.5 — Vision–Brain Integration (`Backend/vision/pipeline/`, `adapter/`)
- `VisionPipelineOrchestrator` coordinating sequential passes and emitting `EventBus` events (`VisionStarted`, `FrameCaptured`, `OCRCompleted`, `UIAnalysisCompleted`, `SceneAnalysisCompleted`, `VisionObservationReady`, `VisionStopped`).
- `VisionAdapter` formatting unified LLM prompt context blocks for `DesktopActionEngine`.
- Refactored `Backend/brain/context.py` using an abstract, extensible `BaseContextProvider` pattern (`DesktopStateContextProvider`, `VisionContextProvider`).

### ✅ Milestone 3.6 — Visual Desktop Assistance & API Endpoints
- Target spatial element grounding in `ToolPlanner` for click requests.
- REST API endpoints in `Backend/main.py` (`/api/vision/status`, `/api/vision/capture`, `/api/vision/start`, `/api/vision/stop`, `/api/vision/pause`, `/api/vision/resume`).

---

## Validation & Performance Benchmarks

- **Phase 3 Audit Verdict**: **✅ PHASE 3 VERIFIED — READY FOR PHASE 4**
- **Snapshot Capture Latency**: `0.040 s` (40 ms)
- **Full Vision Pipeline Latency**: `0.125 s` (125 ms)
- **Phase 1 & Phase 2 Regression Status**: **0 Regressions** (23/23 tools verified).
