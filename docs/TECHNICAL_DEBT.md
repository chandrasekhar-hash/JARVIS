# J.A.R.V.I.S. I2.1 — Technical Debt Register & Known Limitations

## 1. Overview

This document tracks technical debt, deprecation migration status, and non-critical warnings for J.A.R.V.I.S. Version I2.1.

---

## 2. Technical Debt & Migration Status

| Item ID | Description | Status | Target / Resolved Release | Resolution / Mitigation |
|---|---|---|---|---|
| **TD-01** | `google.generativeai` SDK Deprecation | **RESOLVED** | **v1.0.0 (V9 Cleanup)** | Upgraded Gemini Vision & OCR providers to modern `google.genai` SDK (`google-genai` 2.16.0). |
| **TD-02** | Python `asyncio.iscoroutinefunction` Deprecation | **RESOLVED** | **v1.0.0 (V9 Cleanup)** | Replaced `asyncio.iscoroutinefunction` with `inspect.iscoroutinefunction` across performance engine modules. |
| **TD-03** | Repeated Upload File Parsing Logic | **RESOLVED** | **v1.0.0 (V9 Cleanup)** | Consolidated file reading and size/MIME validation into shared `_parse_upload_files` helper in `api/vision.py`. |
| **TD-04** | Frontend Large Bundle Chunking | **RESOLVED** | **v1.0.0 (V9 Cleanup)** | Implemented dynamic `React.lazy` code-splitting for heavy views (`AuthView`, `UserProfileView`, `SetupWizard`, `DiagnosticsView`), creating 6 lazy chunks. |
| **TD-05** | Gemini Free-Tier Quota Limits | Managed | Production Config | Gemini free-tier rate limits (20 req/min) handled gracefully with automatic fallbacks and recovery notices. |

---

## 3. Known System Limitations

1. **Camera Stream Round-Trip**: Local 32x32 dHash + MSE frame selection runs in sub-5.22ms, but LLM visual inference round-trip depends on network latency (~3 seconds).
2. **Ephemeral Memory Scope**: Multimodal context automatically purges after 5 minutes of inactivity; persistent cross-session memory is intentionally excluded by security design.
