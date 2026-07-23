from typing import List, Dict, Any
from pydantic import BaseModel, Field
from memory.models.query import MemoryResult
from tools.telemetry import log_structured, backend_log


class MemoryContextPackage(BaseModel):
    """
    Structured context package containing retrieved memory payloads, scores, sources,
    and LLM-ready context string.
    """
    has_context: bool = False
    memory_count: int = 0
    formatted_context: str = ""
    retrieved_memories: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemoryContextGenerator:
    """
    Converts final ranked and filtered memory results into structured context packages
    and compact LLM-ready context block strings without directly mutating prompt templates.
    """

    def __init__(self, max_memories: int = 5, max_word_budget: int = 500):
        self.max_memories = max_memories
        self.max_word_budget = max_word_budget

    def generate(self, ranked_results: List[MemoryResult]) -> MemoryContextPackage:
        """
        Generates a MemoryContextPackage with structured memory payloads and formatted LLM context.
        """
        top_candidates = ranked_results[:self.max_memories]
        if not top_candidates:
            return MemoryContextPackage(
                has_context=False,
                memory_count=0,
                formatted_context="",
                retrieved_memories=[],
                metadata={"word_count": 0}
            )

        context_lines = ["[Long-Term Memory Context]"]
        retrieved_list = []
        total_words = 0

        for res in top_candidates:
            mem = res.memory
            line = f"- [{mem.type.value.upper()}] {mem.title}: {mem.summary or mem.content[:150]} (Score: {res.score:.2f}, Source: {mem.metadata.source})"
            words_in_line = len(line.split())
            
            if total_words + words_in_line > self.max_word_budget and len(context_lines) > 1:
                break  # Enforce word budget limit

            context_lines.append(line)
            total_words += words_in_line

            retrieved_list.append({
                "memory_id": mem.memory_id,
                "type": mem.type.value,
                "title": mem.title,
                "content": mem.content,
                "summary": mem.summary,
                "score": res.score,
                "matched_by": res.matched_by,
                "source": mem.metadata.source,
                "importance": mem.metadata.importance_score,
                "tags": mem.metadata.tags
            })

        formatted_block = "\n".join(context_lines)

        package = MemoryContextPackage(
            has_context=True,
            memory_count=len(retrieved_list),
            formatted_context=formatted_block,
            retrieved_memories=retrieved_list,
            metadata={
                "word_count": total_words,
                "max_memories": self.max_memories,
                "max_word_budget": self.max_word_budget
            }
        )

        log_structured(backend_log, "INFO", f"[MemoryContextGenerator] Generated context package with {package.memory_count} memories ({total_words} words)")
        return package
