# J.A.R.V.I.S. I2.1 — Testing & Development Guide

## 1. Overview

J.A.R.V.I.S. maintains a comprehensive, zero-regression test architecture covering unit tests, product tests, API integration tests, and performance benchmarks.

---

## 2. Test Execution Commands

### Run Full Vision Intelligence Regression Suite (V2 to V8 + V9 Hardening)
```bash
cd backend
../.venv/bin/python -m unittest test_vision_v2.py test_vision_v3.py test_vision_v4_ocr.py test_vision_v5_screenshot.py test_vision_v6_multi_image.py test_vision_v7_camera.py test_vision_v8_fusion.py test_v9_production_hardening.py
```

### Run Backend Product & Orchestrator Test Suite (pytest)
```bash
PYTHONPATH=backend:backend/Backend ../.venv/bin/pytest backend/tests/test_conversation_phase13.py backend/tests/test_diagnostics_phase18.py backend/tests/test_orchestrator_phase16.py backend/tests/test_performance_phase17.py backend/tests/test_speech_recognition.py backend/tests/test_voice_phase14.py
```

### Run Frontend Linting & Build Verification
```bash
cd frontend
npm run lint
npm run build
```

---

## 3. Test Architecture & Structure

| Test File | Target Subsystem | Assertions / Coverage |
|---|---|---|
| `test_vision_v2.py` | V2 Real Vision Engine | API parameters, file validation, vision results |
| `test_vision_v3.py` | V3 Advanced Vision | Task classification, single-pass summaries, domain prompts |
| `test_vision_v4_ocr.py` | V4 OCR Intelligence | Text extraction, receipt/code routing, CER calculation |
| `test_vision_v5_screenshot.py` | V5 Screenshot Intelligence | IDE, terminal, browser, dashboard classification |
| `test_vision_v6_multi_image.py` | V6 Advanced Multi-Image | Relationship tags, G-Eval comparison, duplicate detection |
| `test_vision_v7_camera.py` | V7 Camera Vision | Ephemeral sessions, dHash + MSE scene detection, focus continuity |
| `test_vision_v8_fusion.py` | V8 Voice + Vision Fusion | Pronoun resolution, multi-signal capability router, clarification |
| `test_v9_production_hardening.py` | V9 System Hardening | Upload limits, error masking, leak-free memory, observability |
