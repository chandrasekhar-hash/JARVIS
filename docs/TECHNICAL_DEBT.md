# J.A.R.V.I.S. Technical Debt Register

**Release Version**: 7.0.1  
**Last Updated**: 2026-07-26  
**Status**: Active Maintenance Tracking  

This register documents accepted architectural trade-offs, deferred enhancements, known limitations, and future maintainability tasks across the codebase.

---

## 1. Technical Debt Inventory

| ID | Title & Description | Category | Priority | Estimated Effort | Status | Target Milestone |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **DEBT-001** | **In-Memory Cache Invalidation Scaling**: Current `PreferenceStore` and `SessionManager` caches use in-process dictionaries. Must be linked to `CacheManager` for multi-worker support. | Caching | Medium | 1 Person-Day | Accepted Trade-off | Phase 8.1 |
| **DEBT-002** | **Keyword-Based Intent Classification**: `IntentForecaster` uses regex keyword matching for intent classification. Works in $< 1\text{ ms}$, but complex multi-intent sentences could benefit from vector embedding fallback. | AI / NLP | Low | 2 Person-Days | Deferred Enhancement | Phase 8.2 |
| **DEBT-003** | **Event Bus Rate Limiting**: `EventBus` uses bounded history queues with drop-oldest overflow policy, but lacks per-event-name token bucket rate limiting. | Infrastructure | Low | 1 Person-Day | Deferred Enhancement | Phase 8.3 |
| **DEBT-004** | **Database Connection Pooling**: Relational SQLite storage drivers in Phase 4 initialize separate connection handles per thread. Connection pool abstraction will improve high-concurrency throughput. | Persistence | Medium | 2 Person-Days | Accepted Trade-off | Phase 8.1 |
| **DEBT-005** | **Mock Tool Telemetry Tracing**: Desktop vision element grounding in mock mode generates synthetic telemetry traces. Integration with live OS display capture needed for cross-platform deployments. | Multimodal | Low | 3 Person-Days | Deferred Enhancement | Phase 8.4 |

---

## 2. Deferred Enhancements & Rationale

### DEBT-001: Distributed Cache Scaling
- **Rationale**: For single-process desktop assistant deployments (FastAPI + Tauri UI), in-process `MemoryCacheProvider` delivers sub-millisecond latencies ($< 0.1\text{ ms}$) without requiring external Redis processes or network overhead.
- **Future Resolution**: `CacheManager` abstraction created in Patch 7.0.1 allows zero-code-change Redis migration when multi-device syncing is introduced in Phase 8.

### DEBT-002: Keyword Intent Forecasting
- **Rationale**: Regex keyword pattern matching satisfies the $< 100\text{ ms}$ prediction SLA target easily (measured at $\approx 2.5\text{ ms}$). Adding a local LLM call or vector embedding search for every background prediction would add $50\text{--}150\text{ ms}$ latency.
- **Future Resolution**: Hybrid keyword + vector similarity pipeline will be added as an optional high-precision mode in Phase 8.
