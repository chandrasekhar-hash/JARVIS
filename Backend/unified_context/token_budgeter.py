from typing import List, Dict, Any
from unified_context.models import ContextChunk, ContextPriority, TokenAllocation
from tools.telemetry import log_structured, backend_log


class TokenBudgeter:
    """
    Allocates context token quotas based on priority weighting, trims overflow chunks,
    and enforces maximum token budgets.
    """

    def __init__(self, default_max_budget: int = 4096):
        self.default_max_budget = default_max_budget

    def estimate_tokens(self, text: str) -> int:
        """Simple deterministic token estimation (approx 4 chars per token)."""
        if not text:
            return 0
        return max(1, len(text) // 4)

    def allocate_tokens(
        self, chunks: List[ContextChunk], max_budget: int = 4096
    ) -> List[ContextChunk]:
        try:
            if not chunks:
                return []

            budget = max_budget or self.default_max_budget

            # Sort chunks by priority (CRITICAL=1 comes first), then timestamp
            sorted_chunks = sorted(
                chunks, key=lambda c: (c.priority.value, -c.timestamp)
            )

            result_chunks: List[ContextChunk] = []
            used_tokens = 0

            for chunk in sorted_chunks:
                chunk_tokens = chunk.estimated_tokens or self.estimate_tokens(chunk.content)

                if used_tokens + chunk_tokens <= budget:
                    result_chunks.append(chunk)
                    used_tokens += chunk_tokens
                else:
                    # Overflow: if CRITICAL or HIGH, try to trim content
                    remaining_budget = budget - used_tokens
                    if remaining_budget >= 20 and chunk.priority <= ContextPriority.HIGH:
                        # Trim content to fit remaining budget
                        max_chars = remaining_budget * 4
                        trimmed_content = chunk.content[:max_chars] + "... [TRIMMED]"
                        trimmed_tokens = self.estimate_tokens(trimmed_content)

                        trimmed_chunk = ContextChunk(
                            chunk_id=chunk.chunk_id,
                            source=chunk.source,
                            provider_id=chunk.provider_id,
                            content=trimmed_content,
                            priority=chunk.priority,
                            estimated_tokens=trimmed_tokens,
                            metadata={**chunk.metadata, "trimmed": True},
                            timestamp=chunk.timestamp,
                        )
                        result_chunks.append(trimmed_chunk)
                        used_tokens += trimmed_tokens
                    break  # Stop adding further lower-priority chunks once budget filled

            log_structured(
                backend_log,
                "INFO",
                f"[TokenBudgeter] Budgeted {len(result_chunks)}/{len(chunks)} chunks ({used_tokens}/{budget} tokens)",
            )
            return result_chunks

        except Exception as e:
            log_structured(backend_log, "ERROR", f"[TokenBudgeter] Error allocating tokens: {str(e)}")
            return chunks[:3]
