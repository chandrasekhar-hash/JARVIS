"""
JARVIS Product 1.6 - Knowledge Telemetry.
Tracks metrics for document indexing, chunk count, embedding latency, retrieval, and cache hits.
"""

from typing import Dict, Any


class KnowledgeTelemetry:
    def __init__(self):
        self.documents_indexed = 0
        self.total_chunks = 0
        self.embedding_count = 0
        self.cache_hits = 0
        self.query_count = 0

    def record_ingestion(self, num_chunks: int):
        self.documents_indexed += 1
        self.total_chunks += num_chunks

    def record_embedding(self, count: int, hits: int):
        self.embedding_count += count
        self.cache_hits += hits

    def record_query(self):
        self.query_count += 1

    def get_metrics(self) -> Dict[str, Any]:
        hit_rate = (self.cache_hits / max(1, self.embedding_count)) * 100.0
        return {
            "documents_indexed": self.documents_indexed,
            "total_chunks": self.total_chunks,
            "embedding_count": self.embedding_count,
            "cache_hits": self.cache_hits,
            "cache_hit_rate_pct": round(hit_rate, 2),
            "query_count": self.query_count,
        }


knowledge_telemetry = KnowledgeTelemetry()
