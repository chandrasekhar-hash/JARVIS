import time
from typing import Optional, Dict, Any, List
from brain.event_bus import event_bus
from memory.manager import memory_manager, MemoryManager
from memory.models.memory import Memory, MemoryChunk
from memory.ingestion.capture import RawObservation, ObservationCapture
from memory.ingestion.validator import ObservationValidator, ValidationResult
from memory.ingestion.classifier import ObservationClassifier
from memory.ingestion.deduplicator import ObservationDeduplicator
from tools.telemetry import log_structured, backend_log


class IngestionPipeline:
    """
    Orchestrates the Memory Ingestion Pipeline following Phase 4 architecture:
    Capture -> Validate -> Classify -> Deduplicate -> MemoryManager.store_memory().
    """

    def __init__(self, manager: Optional[MemoryManager] = None, similarity_threshold: float = 0.90):
        self.manager = manager or memory_manager
        self.validator = ObservationValidator()
        self.classifier = ObservationClassifier()
        self.deduplicator = ObservationDeduplicator(similarity_threshold=similarity_threshold)

    async def process_observation(self, observation: RawObservation) -> Optional[str]:
        """
        Processes a RawObservation through all pipeline stages and persists clean memory via MemoryManager.
        Returns memory_id if successfully stored, or None if rejected/deduplicated.
        """
        # 1. CAPTURE EVENT
        event_bus.emit(
            "ObservationCaptured",
            observation_id=observation.observation_id,
            source=observation.source,
            title=observation.title
        )
        log_structured(backend_log, "INFO", f"[IngestionPipeline] Captured observation '{observation.title}' ({observation.source})")

        # 2. VALIDATION STAGE
        val_result: ValidationResult = self.validator.validate(observation)
        if not val_result.is_valid:
            event_bus.emit(
                "ObservationRejected",
                observation_id=observation.observation_id,
                reason=val_result.reason
            )
            log_structured(backend_log, "WARNING", f"[IngestionPipeline] Rejected observation '{observation.observation_id}': {val_result.reason}")
            return None

        event_bus.emit(
            "ObservationValidated",
            observation_id=observation.observation_id,
            status="valid"
        )

        # 3. CLASSIFICATION STAGE
        memory_type, metadata = self.classifier.classify(observation)
        event_bus.emit(
            "ObservationClassified",
            observation_id=observation.observation_id,
            assigned_type=memory_type.value,
            importance=metadata.importance_score
        )
        log_structured(backend_log, "INFO", f"[IngestionPipeline] Classified observation as '{memory_type.value}' (Importance={metadata.importance_score})")

        # 4. DEDUPLICATION STAGE
        existing_memories = await self.manager.list_memories(limit=1000)
        is_dup, matched_id = self.deduplicator.is_duplicate(observation, existing_memories)
        if is_dup:
            event_bus.emit(
                "ObservationDeduplicated",
                observation_id=observation.observation_id,
                matched_memory_id=matched_id,
                action="duplicate_prevented"
            )
            log_structured(backend_log, "INFO", f"[IngestionPipeline] Duplicate detected for observation '{observation.observation_id}'. Storage skipped.")
            return None

        # 5. CONSTRUCT MEMORY OBJECT & STORE VIA MEMORYMANAGER
        chunks = [
            MemoryChunk(
                memory_id=observation.observation_id,
                content=observation.content,
                chunk_index=0
            )
        ]

        memory = Memory(
            memory_id=observation.observation_id,
            type=memory_type,
            title=observation.title or "Ingested Memory",
            content=observation.content,
            summary=observation.content[:150],
            chunks=chunks,
            metadata=metadata
        )

        # Store via MemoryManager
        mem_id = await self.manager.store_memory(memory)
        log_structured(backend_log, "INFO", f"[IngestionPipeline] Successfully ingested & stored memory '{mem_id}'")
        return mem_id


# Singleton instance of IngestionPipeline
ingestion_pipeline = IngestionPipeline()
