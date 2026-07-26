# J.A.R.V.I.S. API Stability Classification

**Release Version**: 7.0.1  
**Classification Date**: 2026-07-26  
**Status**: Active Specification  

This document classifies every public API, protocol, data model, and provider interface across the J.A.R.V.I.S. codebase according to its stability guarantee.

---

## 1. Classification Definitions

| Classification Level | Definition & Guarantee |
| :--- | :--- |
| **Stable** | Production-ready contract. Guaranteed backward compatibility across patch and minor releases. No breaking changes without major version deprecation notices. |
| **Internal** | Private implementation details. Subject to change or refactoring without public notice. Internal to subsystem packages. |
| **Experimental** | New feature under validation. May undergo minor interface refinements in upcoming releases based on empirical telemetry. |
| **Future** | Abstract protocols and interfaces reserved for future phase implementations (e.g. Phase 8 Cross-Platform Sync). |

---

## 2. API Stability Matrix

### 2.1 Core AI Runtime & Desktop Action Engine (Phases 1–3)
| API / Component | Module Path | Classification | Target Deprecation |
| :--- | :--- | :--- | :--- |
| `FastAPI REST & SSE /api/chat` | `Backend/main.py` | **Stable** | None |
| `ToolRegistry` (`@registry.register`) | `Backend/tools/registry.py` | **Stable** | None |
| `IntentClassifier` | `Backend/tools/classifier.py` | **Stable** | None |
| `AgentRouter` | `Backend/tools/router.py` | **Stable** | None |
| `EventBus` (`subscribe`, `emit`) | `Backend/brain/event_bus.py` | **Stable** | None |

### 2.2 Memory Subsystem & Knowledge Graph (Phase 4)
| API / Component | Module Path | Classification | Target Deprecation |
| :--- | :--- | :--- | :--- |
| `BaseMemoryStorageProvider` | `Backend/memory/storage/base.py` | **Stable** | None |
| `SQLiteMemoryStorageProvider` | `Backend/memory/storage/sqlite_provider.py` | **Stable** | None |
| `CosineVectorStorageProvider` | `Backend/memory/storage/vector_provider.py` | **Stable** | None |
| `KnowledgeGraphStorageProvider` | `Backend/memory/storage/graph_provider.py` | **Stable** | None |

### 2.3 Autonomous Execution Subsystem (Phase 5 & 6)
| API / Component | Module Path | Classification | Target Deprecation |
| :--- | :--- | :--- | :--- |
| `CognitiveReasoningEngine` | `Backend/cognitive/reasoning_engine.py` | **Stable** | None |
| `PostExecutionReflectionEngine` | `Backend/cognitive/reflection_engine.py` | **Stable** | None |
| `AdaptivePlannerBridge` | `Backend/cognitive/adaptive_bridge.py` | **Stable** | None |
| `MultiGoalCoordinator` | `Backend/cognitive/multi_goal_coordinator.py` | **Stable** | None |

### 2.4 Phase 7 Cognitive Subsystems (7.1 – 7.6)
| API / Component | Module Path | Classification | Target Deprecation |
| :--- | :--- | :--- | :--- |
| `LearningEngine` | `Backend/learning/engine.py` | **Stable** | None |
| `ILearningEngine` | `Backend/learning/interfaces.py` | **Stable** | None |
| `LearningFeedback`, `RewardSignal` | `Backend/learning/models.py` | **Stable** | None |
| `UserContextProvider` | `Backend/user_model/provider.py` | **Stable** | None |
| `ILongTermUserModel` | `Backend/user_model/interfaces.py` | **Stable** | None |
| `UserProfile`, `UserPreference` | `Backend/user_model/models.py` | **Stable** | None |
| `PredictiveGoalEngine` | `Backend/predictive/engine.py` | **Stable** | None |
| `GoalPrediction`, `Suggestion` | `Backend/predictive/models.py` | **Stable** | None |
| `UnifiedContextEngine` | `Backend/unified_context/engine.py` | **Stable** | None |
| `ProviderRegistry` | `Backend/unified_context/provider_registry.py` | **Stable** | None |
| `CognitiveContext`, `ContextChunk` | `Backend/unified_context/models.py` | **Stable** | None |
| `ConversationContinuityEngine` | `Backend/conversation/engine.py` | **Stable** | None |
| `ConversationSession`, `Topic` | `Backend/conversation/models.py` | **Stable** | None |
| `SelfOptimizationEngine` | `Backend/self_optimization/engine.py` | **Stable** | None |
| `OptimisationReport` | `Backend/self_optimization/models.py` | **Stable** | None |

### 2.5 Common Infrastructure (Patch 7.0.1)
| API / Component | Module Path | Classification | Target Deprecation |
| :--- | :--- | :--- | :--- |
| `BaseCacheProvider` | `Backend/common/cache/interfaces.py` | **Stable** | None |
| `MemoryCacheProvider` | `Backend/common/cache/memory_cache.py` | **Stable** | None |
| `CacheManager` | `Backend/common/cache/cache_manager.py` | **Stable** | None |
| `Distributed Redis Provider` | `Backend/common/cache/` | **Future** | Reserved for Phase 8 |
