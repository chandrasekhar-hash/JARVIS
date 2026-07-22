# JARVIS Architecture Documentation (v2.0)

**Architecture Version**: 2.0  
**Status**: Frozen 🧊  

---

## 1. High-Level Architecture Diagram

```mermaid
graph TD
    Client[Frontend / Client UI] -->|HTTP / SSE Stream| API[FastAPI Entrypoint / main.py]
    API -->|Chat Payload| AIRouter[AI Router / Smart Router]
    AIRouter -->|Active Provider| Providers[AI Providers (Groq / Ollama / Gemini / OpenRouter / Cerebras)]
    API -->|User Intent| Brain[Brain Package (Backend/brain/)]
    
    subgraph Brain ["Brain (Reasoning & Orchestration)"]
        AE[DesktopActionEngine]
        CR[ReferenceResolver]
        DC[DesktopContextManager]
        TP[ToolPlanner]
        PM[PermissionManager]
        EM[ExecutionManager]
        TM[TaskManager]
        EB[EventBus]
    end

    Brain -->|Tool Calls| ToolRegistry[Tool Registry (Backend/tools/registry.py)]
    
    subgraph Tools ["Tools (Action Execution Primitives)"]
        Apps[OS & Apps Control]
        Browser[Browser Automation]
        FS[Filesystem Tools]
        Desktop[Window, Process, Clipboard & Screenshot]
    end

    ToolRegistry --> Tools
    Tools --> OS[Host Operating System]
```

```
Frontend / UI
     ↓
Backend API (FastAPI)
     ↓
AI Layer (AI Router / Smart Router / Providers)
     ↓
Brain (Reasoning & Orchestration)
     ↓
Tool Registry
     ↓
Tools (Action Primitives)
     ↓
Operating System (Windows / macOS / Linux)
```

---

## 2. Complete Backend Folder Structure

```
Backend/
├── ai/                      → AI Providers & Routers (Groq, Gemini, OpenRouter, Cerebras, Ollama)
├── brain/                   → Single Source of Reasoning & Orchestration
│   ├── __init__.py          → Brain Package Exports
│   ├── models.py            → Shared ActionPlan, TaskMetadata, Event & Execution Models
│   ├── event_bus.py         → Decoupled Internal Event Bus
│   ├── context.py           → Desktop Context Manager & Selective Injection
│   ├── permissions.py       → Tiered Permission Verification Framework
│   ├── conversation.py      → Conversation Awareness & Pronoun Resolver
│   ├── planner.py           → Intent Analysis & Multi-Step Action Planner
│   ├── task_manager.py      → Background Async Task Execution Engine
│   ├── executor.py          → Execution Pipeline Runner & Recovery Handler
│   └── action_engine.py     → Master Desktop Pipeline Orchestrator
├── tools/                   → Executable Action Primitives & Registry
│   ├── __init__.py          → Legacy Import Aliases & Tool Package Interface
│   ├── registry.py          → Tool Schema & Execution Registry
│   ├── apps.py              → OS Application Launcher & Control Tools
│   ├── app_discovery.py     → Desktop App Discovery & Indexing
│   ├── app_resolver.py      → Fuzzy Application Resolver
│   ├── browser.py           → Browser Automation Tools
│   ├── desktop.py           → Window, Process, Clipboard & Screenshot Tools
│   ├── filesystem.py        → File Reading, Writing, Directory & Operation Tools
│   ├── classifier.py        → Intent Pattern Classifier
│   ├── locks.py             → Execution Mutex Locks
│   ├── logger.py            → Safety & Diagnostic Logger
│   ├── telemetry.py         → Performance Telemetry Manager
│   ├── startup.py           → Startup Diagnostics & Verification
│   └── router.py            → Agent Chat Routing Entrypoint
├── tts_engines/             → TTS Audio Synthesis Engines
├── main.py                  → FastAPI Web Application Server
└── config.py                → System Configuration & Environment Variables
```

---

## 3. Major Directory Responsibilities

- **`ai/`**: Houses model providers (Groq, Ollama, Gemini, OpenRouter, Cerebras), candidate evaluation, latency measurements, and provider-agnostic router (`ai_router`, `smart_router`).
- **`brain/`**: Single source of intelligence, intent understanding, context management, multi-step planning, permission enforcement, background task tracking, and pipeline orchestration.
- **`tools/`**: Executable action primitives. Performs OS, file, browser, and application operations. Tools never contain decision-making or planning logic.
- **`tts_engines/`**: Edge-TTS text-to-speech audio synthesis engine and voice management.
- **`api/`**: HTTP/REST and SSE streaming API routes defined in `main.py`.

---

## 4. Brain Modules Explained

1. **`action_engine.py` (`DesktopActionEngine`)**: Master pipeline coordinator orchestrating Intent Analysis, Reference Resolution, Tool Planning, Permission Checks, Execution, and Task Routing.
2. **`planner.py` (`ToolPlanner`)**: Analyzes intent and constructs structured `ActionPlan` step sequences.
3. **`executor.py` (`ExecutionManager`)**: Runs action plans, validates tool schemas, checks permissions, handles `dry_run=True` mode, and executes step recovery.
4. **`task_manager.py` (`TaskManager`)**: Async background task manager handling task creation, status updates, progress reporting, cancellation, and retries.
5. **`event_bus.py` (`EventBus`)**: Pub/Sub internal event bus decoupling system notifications.
6. **`context.py` (`DesktopContextManager`)**: Tracks desktop state and provides selective prompt context injection.
7. **`conversation.py` (`ReferenceResolver`)**: Resolves pronouns and ambiguous references across chat turns.
8. **`permissions.py` (`PermissionManager`)**: Enforces safety tiers (`SAFE`, `ASK_ONCE`, `ALWAYS_CONFIRM`).
9. **`models.py`**: Shared Pydantic data schemas (`ActionPlan`, `ActionStep`, `TaskMetadata`, `StructuredExecutionLog`, `Event`, `PermissionLevel`).

---

## 5. Execution Pipeline

```
User Request
    ↓
Intent Analysis
    ↓
Conversation Resolution (Resolves pronouns via conversation.py)
    ↓
Planner (Decomposes query into ActionPlan steps in planner.py)
    ↓
Validation (Verifies tool schema & parameters)
    ↓
Permission Manager (Enforces SAFE / ASK_ONCE / ALWAYS_CONFIRM in permissions.py)
    ↓
Execution Manager (Runs steps or delegates to Task Manager)
    ↓
Task Manager (Executes background operations asynchronously if applicable)
    ↓
Tool Registry (Dispatches execution to target tool)
    ↓
Tool (Performs OS / Browser / File action)
    ↓
Response (Streams result to Client UI via SSE)
```

---

## 6. Dependency Flow

```
API (main.py)
    ↓
Brain (brain/*)
    ↓
Tool Registry (tools/registry.py)
    ↓
Tools (tools/apps.py, tools/browser.py, etc.)
```

**Rules**:
- `Brain` $\rightarrow$ `Tool Registry`: Allowed.
- `Tools` $\rightarrow$ `Brain`: **Forbidden**. Tools execute actions without decision logic.

---

## 7. Architecture Freeze Declaration

- **Architecture Version**: `2.0`
- **Status**: **Frozen 🧊**
- Core architecture and dependency rules are frozen. Future development (Phase 3 onwards) will expand capabilities rather than modifying the core pipeline structure.
