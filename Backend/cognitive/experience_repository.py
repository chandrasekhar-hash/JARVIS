import json
import math
import time
from typing import Dict, List, Optional, Any, Union
from pydantic import ValidationError

from cognitive.models import (
    WorkflowTemplate,
    FailurePattern,
    ReflectionReport,
    CognitiveAssessment,
)
from memory.models.memory import (
    Memory,
    MemoryType,
    MemoryMetadata,
    RetentionPolicy,
)
from memory.storage.base import BaseMemoryStorageProvider, BaseVectorStorageProvider
from memory.storage.provider_factory import StorageProviderFactory
from tools.telemetry import log_structured, backend_log


class ExperienceRepository:
    """
    Cognitive abstraction layer over Phase 4 Memory System.
    Stores and retrieves WorkflowTemplates, FailurePatterns, ReflectionReports,
    and CognitiveAssessments using existing relational and vector storage providers.
    Does NOT duplicate storage or perform reasoning/reflection.
    """

    def __init__(
        self,
        memory_storage: Optional[BaseMemoryStorageProvider] = None,
        vector_storage: Optional[BaseVectorStorageProvider] = None
    ):
        if memory_storage is None:
            self.memory_storage = StorageProviderFactory.get_memory_provider()
        else:
            self.memory_storage = memory_storage

        if vector_storage is None:
            self.vector_storage = StorageProviderFactory.get_vector_provider()
        else:
            self.vector_storage = vector_storage

    # ── Storage APIs ─────────────────────────────────────────────────────────

    async def store_workflow_template(self, template: WorkflowTemplate) -> str:
        """Stores or updates a reusable WorkflowTemplate in Phase 4 Memory."""
        try:
            content_json = json.dumps(template.model_dump())
            tags = ["cognitive", "type:workflow_template", f"pattern:{template.goal_pattern}"]
            
            mem = Memory(
                memory_id=template.template_id,
                type=MemoryType.PROCEDURAL,
                title=f"WorkflowTemplate: {template.goal_pattern}",
                content=content_json,
                summary=f"Workflow template for '{template.goal_pattern}' with {len(template.recommended_tasks)} tasks.",
                metadata=MemoryMetadata(
                    importance_score=8.5,
                    source="cognitive_repository",
                    retention_policy=RetentionPolicy.PERMANENT,
                    tags=tags,
                    created_at=template.created_at,
                    updated_at=template.updated_at
                )
            )

            stored_id = await self.memory_storage.store_memory(mem)
            log_structured(backend_log, "INFO", f"[ExperienceRepo] Stored WorkflowTemplate: {template.template_id}")
            return stored_id
        except Exception as e:
            log_structured(backend_log, "ERROR", f"[ExperienceRepo] Failed to store WorkflowTemplate: {str(e)}")
            return ""

    async def store_failure_pattern(self, failure_pattern: FailurePattern) -> str:
        """Stores or updates a FailurePattern in Phase 4 Memory."""
        try:
            content_json = json.dumps(failure_pattern.model_dump())
            tags = ["cognitive", "type:failure_pattern"]

            mem = Memory(
                memory_id=failure_pattern.pattern_id,
                type=MemoryType.PROCEDURAL,
                title=f"FailurePattern: {failure_pattern.error_signature[:50]}",
                content=content_json,
                summary=f"Failure pattern for signature '{failure_pattern.error_signature}'. Workaround: {failure_pattern.suggested_workaround}",
                metadata=MemoryMetadata(
                    importance_score=7.5,
                    source="cognitive_repository",
                    retention_policy=RetentionPolicy.PERMANENT,
                    tags=tags,
                    created_at=failure_pattern.last_seen_at,
                    updated_at=failure_pattern.last_seen_at
                )
            )

            stored_id = await self.memory_storage.store_memory(mem)
            log_structured(backend_log, "INFO", f"[ExperienceRepo] Stored FailurePattern: {failure_pattern.pattern_id}")
            return stored_id
        except Exception as e:
            log_structured(backend_log, "ERROR", f"[ExperienceRepo] Failed to store FailurePattern: {str(e)}")
            return ""

    async def store_reflection(self, reflection: ReflectionReport) -> str:
        """Stores a ReflectionReport in Phase 4 Memory."""
        try:
            content_json = json.dumps(reflection.model_dump())
            tags = ["cognitive", "type:reflection_report", f"goal:{reflection.goal_id}"]

            mem = Memory(
                memory_id=reflection.reflection_id,
                type=MemoryType.EPISODIC,
                title=f"ReflectionReport: Goal {reflection.goal_id}",
                content=content_json,
                summary=f"Reflection report for goal '{reflection.goal_id}' (Outcome: {reflection.outcome.value}).",
                metadata=MemoryMetadata(
                    importance_score=6.5,
                    source="cognitive_repository",
                    retention_policy=RetentionPolicy.EPISODIC,
                    tags=tags,
                    created_at=reflection.created_at,
                    updated_at=reflection.created_at
                )
            )

            stored_id = await self.memory_storage.store_memory(mem)
            log_structured(backend_log, "INFO", f"[ExperienceRepo] Stored ReflectionReport: {reflection.reflection_id}")
            return stored_id
        except Exception as e:
            log_structured(backend_log, "ERROR", f"[ExperienceRepo] Failed to store ReflectionReport: {str(e)}")
            return ""

    async def store_assessment(self, assessment: CognitiveAssessment) -> str:
        """Stores a CognitiveAssessment in Phase 4 Memory."""
        try:
            content_json = json.dumps(assessment.model_dump())
            tags = ["cognitive", "type:cognitive_assessment", f"goal:{assessment.goal_id}"]

            mem = Memory(
                memory_id=assessment.assessment_id,
                type=MemoryType.EPISODIC,
                title=f"CognitiveAssessment: Goal {assessment.goal_id}",
                content=content_json,
                summary=f"Assessment for goal '{assessment.goal_id}' (Confidence: {assessment.confidence_score:.2f}, Risk: {assessment.risk_level.value}).",
                metadata=MemoryMetadata(
                    importance_score=6.0,
                    source="cognitive_repository",
                    retention_policy=RetentionPolicy.EPISODIC,
                    tags=tags,
                    created_at=assessment.created_at,
                    updated_at=assessment.created_at
                )
            )

            stored_id = await self.memory_storage.store_memory(mem)
            log_structured(backend_log, "INFO", f"[ExperienceRepo] Stored CognitiveAssessment: {assessment.assessment_id}")
            return stored_id
        except Exception as e:
            log_structured(backend_log, "ERROR", f"[ExperienceRepo] Failed to store CognitiveAssessment: {str(e)}")
            return ""

    # ── Retrieval APIs ───────────────────────────────────────────────────────

    async def get_workflow_template(self, template_id: str) -> Optional[WorkflowTemplate]:
        """Retrieves a WorkflowTemplate by ID."""
        try:
            mem = await self.memory_storage.get_memory(template_id)
            if not mem:
                return None
            data = json.loads(mem.content)
            return WorkflowTemplate.model_validate(data)
        except Exception as e:
            log_structured(backend_log, "WARNING", f"[ExperienceRepo] Error reading template '{template_id}': {str(e)}")
            return None

    async def get_failure_pattern(self, pattern_id: str) -> Optional[FailurePattern]:
        """Retrieves a FailurePattern by ID."""
        try:
            mem = await self.memory_storage.get_memory(pattern_id)
            if not mem:
                return None
            data = json.loads(mem.content)
            return FailurePattern.model_validate(data)
        except Exception as e:
            log_structured(backend_log, "WARNING", f"[ExperienceRepo] Error reading failure pattern '{pattern_id}': {str(e)}")
            return None

    async def get_reflection(self, reflection_id: str) -> Optional[ReflectionReport]:
        """Retrieves a ReflectionReport by ID."""
        try:
            mem = await self.memory_storage.get_memory(reflection_id)
            if not mem:
                return None
            data = json.loads(mem.content)
            return ReflectionReport.model_validate(data)
        except Exception as e:
            log_structured(backend_log, "WARNING", f"[ExperienceRepo] Error reading reflection '{reflection_id}': {str(e)}")
            return None

    async def get_assessment(self, assessment_id: str) -> Optional[CognitiveAssessment]:
        """Retrieves a CognitiveAssessment by ID."""
        try:
            mem = await self.memory_storage.get_memory(assessment_id)
            if not mem:
                return None
            data = json.loads(mem.content)
            return CognitiveAssessment.model_validate(data)
        except Exception as e:
            log_structured(backend_log, "WARNING", f"[ExperienceRepo] Error reading assessment '{assessment_id}': {str(e)}")
            return None

    async def get_failure_patterns(
        self,
        error_signature: Optional[str] = None,
        limit: int = 10
    ) -> List[FailurePattern]:
        """Retrieves matching FailurePatterns filtered by error signature."""
        try:
            memories = await self.memory_storage.list_memories(tag="type:failure_pattern", limit=100)
            patterns: List[FailurePattern] = []

            for mem in memories:
                try:
                    data = json.loads(mem.content)
                    fp = FailurePattern.model_validate(data)
                    if error_signature:
                        if error_signature.lower() in fp.error_signature.lower() or fp.error_signature.lower() in error_signature.lower():
                            patterns.append(fp)
                    else:
                        patterns.append(fp)
                except Exception:
                    continue

            # Sort by occurrence count & recency
            patterns.sort(key=lambda x: (x.occurrence_count, x.last_seen_at), reverse=True)
            return patterns[:limit]
        except Exception as e:
            log_structured(backend_log, "ERROR", f"[ExperienceRepo] Failed to retrieve failure patterns: {str(e)}")
            return []

    # ── Search & Ranking APIs ────────────────────────────────────────────────

    async def search_similar_experiences(
        self,
        query_text: str,
        experience_type: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Performs semantic and keyword retrieval over experiences,
        ranking results by relevance, success count, reuse frequency, and recency.
        """
        try:
            tag_filter = f"type:{experience_type}" if experience_type else "cognitive"
            memories = await self.memory_storage.list_memories(tag=tag_filter, limit=100)

            query_tokens = set(query_text.lower().split()) if query_text else set()
            now = time.time()
            scored_results = []

            for mem in memories:
                try:
                    data = json.loads(mem.content)
                    title = mem.title.lower()
                    summary = mem.summary.lower()
                    content = mem.content.lower()

                    # 1. Relevance Score (Token overlap)
                    if query_tokens:
                        matched_tokens = sum(
                            1 for tok in query_tokens
                            if tok.lower() in title or tok.lower() in summary or tok.lower() in content
                        )
                        if matched_tokens == 0:
                            continue
                        relevance = matched_tokens / len(query_tokens)
                    else:
                        relevance = 0.5

                    # Extract stats
                    success_count = data.get("success_count", 1)
                    avg_duration = data.get("average_duration_sec", 1.0)
                    confidence = data.get("confidence_score", mem.metadata.confidence)
                    created_at = data.get("created_at", mem.metadata.created_at)

                    # 2. Recency Decay (30-day halflife)
                    age_days = max(0.0, (now - created_at) / 86400.0)
                    recency_score = math.exp(-age_days / 30.0)

                    # 3. Log-scaled Reuse Score
                    reuse_score = math.log10(success_count + 1)

                    # Total Composite Rank Score
                    rank_score = (relevance * 0.40) + (confidence * 0.25) + (min(1.0, reuse_score) * 0.15) + (recency_score * 0.20)

                    scored_results.append({
                        "memory_id": mem.memory_id,
                        "title": mem.title,
                        "experience_type": next((t.split(":")[1] for t in mem.metadata.tags if t.startswith("type:")), "unknown"),
                        "data": data,
                        "relevance_score": relevance,
                        "rank_score": rank_score
                    })
                except Exception:
                    continue

            # Sort descending by composite rank score
            scored_results.sort(key=lambda x: x["rank_score"], reverse=True)
            return scored_results[:limit]
        except Exception as e:
            log_structured(backend_log, "ERROR", f"[ExperienceRepo] search_similar_experiences failed: {str(e)}")
            return []

    async def get_best_matching_template(self, goal_text: str) -> Optional[WorkflowTemplate]:
        """Retrieves the single highest-ranked WorkflowTemplate for a goal prompt."""
        results = await self.search_similar_experiences(query_text=goal_text, experience_type="workflow_template", limit=1)
        if not results:
            return None
        try:
            data = results[0]["data"]
            return WorkflowTemplate.model_validate(data)
        except Exception:
            return None

    # ── Experience Statistics Updates ────────────────────────────────────────

    async def update_success_statistics(self, template_id: str, execution_time_sec: float) -> bool:
        """Updates success counter and running average execution time for a WorkflowTemplate."""
        try:
            tmpl = await self.get_workflow_template(template_id)
            if not tmpl:
                return False

            new_success_count = tmpl.success_count + 1
            # Running average update
            new_avg_duration = (
                (tmpl.average_duration_sec * tmpl.success_count) + execution_time_sec
            ) / new_success_count

            updated_tmpl = WorkflowTemplate(
                template_id=tmpl.template_id,
                goal_pattern=tmpl.goal_pattern,
                recommended_tasks=tmpl.recommended_tasks,
                success_count=new_success_count,
                average_duration_sec=new_avg_duration,
                created_at=tmpl.created_at,
                updated_at=time.time()
            )

            res_id = await self.store_workflow_template(updated_tmpl)
            return bool(res_id)
        except Exception as e:
            log_structured(backend_log, "ERROR", f"[ExperienceRepo] Failed to update success stats for '{template_id}': {str(e)}")
            return False

    async def update_failure_statistics(self, pattern_id: str) -> bool:
        """Increments occurrence counter and updates timestamp for a FailurePattern."""
        try:
            fp = await self.get_failure_pattern(pattern_id)
            if not fp:
                return False

            updated_fp = FailurePattern(
                pattern_id=fp.pattern_id,
                error_signature=fp.error_signature,
                root_cause=fp.root_cause,
                suggested_workaround=fp.suggested_workaround,
                occurrence_count=fp.occurrence_count + 1,
                last_seen_at=time.time()
            )

            res_id = await self.store_failure_pattern(updated_fp)
            return bool(res_id)
        except Exception as e:
            log_structured(backend_log, "ERROR", f"[ExperienceRepo] Failed to update failure stats for '{pattern_id}': {str(e)}")
            return False

    async def increment_reuse_count(self, template_id: str) -> bool:
        """Increments reuse count for a WorkflowTemplate."""
        return await self.update_success_statistics(template_id, execution_time_sec=0.0)

    async def delete_experience(self, experience_id: str) -> bool:
        """Deletes an experience record from Phase 4 Memory."""
        try:
            return await self.memory_storage.delete_memory(experience_id)
        except Exception as e:
            log_structured(backend_log, "ERROR", f"[ExperienceRepo] Failed to delete experience '{experience_id}': {str(e)}")
            return False


experience_repository = ExperienceRepository()
