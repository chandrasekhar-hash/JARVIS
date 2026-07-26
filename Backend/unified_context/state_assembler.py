import time
from typing import List, Dict, Set, Any
from unified_context.models import ContextChunk, ContextPriority
from unified_context.interfaces import IContextProvider
from tools.telemetry import log_structured, backend_log


class StateAssembler:
    """
    Collects raw context chunks from registered providers, merges them,
    deduplicates repeated content, and ranks by priority.
    """

    def __init__(self):
        pass

    def collect_and_merge(
        self, providers: List[IContextProvider], user_id: str
    ) -> List[ContextChunk]:
        raw_chunks: List[ContextChunk] = []

        # 1. Parallel / Sequential Context Collection
        for provider in providers:
            try:
                if provider.check_health():
                    fetched = provider.fetch_context(user_id=user_id, max_tokens=1000)
                    raw_chunks.extend(fetched)
            except Exception as p_err:
                log_structured(
                    backend_log,
                    "WARNING",
                    f"[StateAssembler] Provider '{provider.provider_info.provider_id}' failed: {str(p_err)}",
                )

        # 2. Content Deduplication
        deduped_chunks: List[ContextChunk] = []
        seen_content_hashes: Set[str] = set()

        for chunk in raw_chunks:
            # Simple content hash for exact deduplication
            content_snippet = chunk.content.strip().lower()[:100]
            if content_snippet not in seen_content_hashes:
                seen_content_hashes.add(content_snippet)
                deduped_chunks.append(chunk)

        # 3. Priority Ranking (CRITICAL=1 comes first)
        deduped_chunks.sort(key=lambda c: (c.priority.value, -c.timestamp))

        log_structured(
            backend_log,
            "INFO",
            f"[StateAssembler] Collected {len(raw_chunks)} chunks, deduped to {len(deduped_chunks)} chunks",
        )
        return deduped_chunks
