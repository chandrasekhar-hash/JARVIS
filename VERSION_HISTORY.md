# JARVIS Version History

---

## **v3.0.0 — JARVIS Vision & Multimodal Intelligence (Current Stable Release)**
- **Release Date**: July 2026
- **Architecture**: 3.0 (Frozen)
- **Key Milestones**:
  - Screen capture subsystem with multi-monitor & Win32 GDI / Pillow fallbacks
  - Spatial OCR text extraction preserving top-to-bottom, left-to-right reading order
  - Desktop UI understanding supporting 17 element types and spatial coordinate grounding (`element_grounding_engine`)
  - Scene & workflow classification (`SceneAnalyzer`) and visual change detection (`ChangeDetector`)
  - Short-term visual memory timeline manager (`VisualContextManager`)
  - `VisionPipelineOrchestrator` & `VisionAdapter` LLM prompt context formatting
  - Extensible `BaseContextProvider` registry in `Backend/brain/context.py`
  - Vision REST API endpoints (`/api/vision/status`, `/api/vision/capture`, `/api/vision/start`, `/api/vision/stop`)

---

## **v2.0.0 — JARVIS Desktop Intelligence**
- **Release Date**: July 2026
- **Architecture**: 2.0 (Frozen)
- **Key Milestones**:
  - Consolidation of intelligence & decision modules into `Backend/brain/`
  - Master pipeline `DesktopActionEngine` (`Intent Analysis -> Planner -> Validation -> Permission Manager -> Execution Manager -> Response`)
  - Multi-step tool planning & workflow chaining
  - Asynchronous background `TaskManager`
  - Decoupled internal `EventBus`
  - Desktop Context Manager & selective prompt context injection
  - Pronoun reference resolution across chat turns
  - Tiered permission enforcement (`SAFE`, `ASK_ONCE`, `ALWAYS_CONFIRM`)

---

## **v1.0.0 — Multi-Provider AI Runtime**
- **Release Date**: July 2026
- **Key Milestones**:
  - Multi-provider AI abstraction layer (Groq, Gemini, OpenRouter, Cerebras, Ollama)
  - AIRouter & SmartRouter priority and latency evaluation
  - Live failover pathways
  - SSE streaming event pipeline & Edge-TTS speech synthesis integration

---

## **v0.x — Prototype & Proof of Concept**
- **Key Milestones**:
  - Initial direct tool execution & intent classification prototype
  - Early desktop control scripts

---

## **Future Releases**
- **v4.0.0**: Persistent Long-Term Memory & Local RAG Knowledge Graph
- **v5.0.0**: Plugin SDK & Ecosystem Extension
