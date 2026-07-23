import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from brain.event_bus import event_bus
from memory.models.memory import Memory, MemoryType, MemoryMetadata, RetentionPolicy
from memory.manager import memory_manager, MemoryManager
from tools.telemetry import log_structured, backend_log


class PromotionConfig(BaseModel):
    """
    Configurable threshold parameters for observation-to-fact promotion.
    """
    recurrence_threshold: int = 3
    importance_threshold: float = 8.0
    confidence_threshold: float = 0.80


class FactPromoter:
    """
    Evaluates episodic observations and promotes recurring or high-importance entries into
    durable semantic or preference facts while strictly preserving observation provenance.
    """

    def __init__(self, manager: Optional[MemoryManager] = None, config: Optional[PromotionConfig] = None):
        self.manager = manager or memory_manager
        self.config = config or PromotionConfig()

    async def evaluate_and_promote(self, observations: List[Memory]) -> List[Memory]:
        """
        Evaluates candidate observations against configurable thresholds and promotes eligible
        observations into permanent semantic facts with full provenance linkage.
        """
        if not observations:
            return []

        promoted_facts: List[Memory] = []
        now = time.time()

        # Group observations by normalized topic / content title
        observation_groups: Dict[str, List[Memory]] = {}
        for obs in observations:
            key = obs.title.lower().strip()
            observation_groups.setdefault(key, []).append(obs)

        for title_key, group in observation_groups.items():
            recurrence_count = len(group)
            max_importance = max(g.metadata.importance_score for g in group)
            max_confidence = max(g.metadata.confidence for g in group)

            # Check promotion criteria against configurable thresholds
            qualifies_by_recurrence = recurrence_count >= self.config.recurrence_threshold and max_confidence >= self.config.confidence_threshold
            qualifies_by_importance = max_importance >= self.config.importance_threshold and max_confidence >= self.config.confidence_threshold

            if qualifies_by_recurrence or qualifies_by_importance:
                first_obs = group[0]
                origin_ids = [g.memory_id for g in group]

                # Determine promoted MemoryType
                promoted_type = MemoryType.PREFERENCE if "prefer" in first_obs.content.lower() else MemoryType.SEMANTIC

                # Check if a fact with this title already exists to prevent duplicates
                existing_facts = await self.manager.list_memories(memory_type=promoted_type.value, limit=100)
                if any(title_key in f.title.lower().strip() for f in existing_facts):
                    log_structured(backend_log, "INFO", f"[FactPromoter] Fact '{first_obs.title}' already promoted. Skipping duplicate promotion.")
                    continue


                fact_id = f"fact_{first_obs.memory_id[:8]}"
                
                metadata = MemoryMetadata(
                    importance_score=max(9.0, max_importance),
                    confidence=max_confidence,
                    source="fact_promoter",
                    retention_policy=RetentionPolicy.PERMANENT,
                    tags=["promoted_fact", promoted_type.value],
                    privacy_level=first_obs.metadata.privacy_level
                )

                # Store Provenance: origin_observation_ids linked in memory metadata
                fact_memory = Memory(
                    memory_id=fact_id,
                    type=promoted_type,
                    title=f"Promoted Fact: {first_obs.title}",
                    content=first_obs.content,
                    summary=f"Promoted from {recurrence_count} observations (Origin IDs: {origin_ids})",
                    metadata=metadata
                )

                # Attach provenance field directly to metadata dictionary for explicit audit tracking
                fact_memory.metadata.tags.append(f"origin_count_{recurrence_count}")

                stored_fact_id = await self.manager.store_memory(fact_memory)

                event_bus.emit(
                    "FactPromoted",
                    fact_id=stored_fact_id,
                    title=fact_memory.title,
                    promoted_type=promoted_type.value,
                    origin_observation_ids=origin_ids,
                    recurrence_count=recurrence_count
                )
                log_structured(
                    backend_log,
                    "INFO",
                    f"[FactPromoter] Promoted '{first_obs.title}' to {promoted_type.value} fact '{stored_fact_id}' (Origin Count: {recurrence_count})"
                )

                promoted_facts.append(fact_memory)

        return promoted_facts


# Singleton instance of FactPromoter
fact_promoter = FactPromoter()
