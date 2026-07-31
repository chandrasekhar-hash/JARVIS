"""
JARVIS Product 1.6 - SQLite Vector Store.
Production default storing vector embeddings in SQLite with Cosine Distance calculation.
"""

import sqlite3
import json
import math
import struct
import logging
from typing import List, Dict, Any, Tuple, Optional
from .vector_base import VectorStoreBase

logger = logging.getLogger(__name__)


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    if len(v1) != len(v2) or not v1:
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class SQLiteVectorStore(VectorStoreBase):
    def __init__(self, db_path: str = "logs/jarvis_knowledge.db"):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        conn = self._get_connection()
        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS knowledge_vectors (
                        chunk_id TEXT PRIMARY KEY,
                        document_id TEXT NOT NULL,
                        vector_blob BLOB NOT NULL,
                        dimension INTEGER NOT NULL,
                        metadata_json TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_vectors_doc_id ON knowledge_vectors(document_id);")
        finally:
            conn.close()

    def add_vectors(
        self,
        chunk_ids: List[str],
        vectors: List[List[float]],
        metadatas: List[Dict[str, Any]],
    ) -> bool:
        if not chunk_ids or len(chunk_ids) != len(vectors):
            return False

        conn = self._get_connection()
        try:
            with conn:
                for chunk_id, vec, meta in zip(chunk_ids, vectors, metadatas):
                    doc_id = meta.get("document_id", "")
                    vec_blob = struct.pack(f"{len(vec)}f", *vec)
                    meta_str = json.dumps(meta)
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO knowledge_vectors (chunk_id, document_id, vector_blob, dimension, metadata_json)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (chunk_id, doc_id, vec_blob, len(vec), meta_str),
                    )
            return True
        except Exception as e:
            logger.error(f"SQLiteVectorStore add_vectors error: {e}")
            return False
        finally:
            conn.close()

    def search_vectors(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[str, float]]:
        conn = self._get_connection()
        results: List[Tuple[str, float]] = []
        try:
            allowed_doc_ids = filters.get("allowed_doc_ids") if filters else None
            
            query_sql = "SELECT chunk_id, vector_blob, dimension, document_id FROM knowledge_vectors"
            params = []
            if allowed_doc_ids is not None:
                if not allowed_doc_ids:
                    return []
                placeholders = ",".join(["?"] * len(allowed_doc_ids))
                query_sql += f" WHERE document_id IN ({placeholders})"
                params = allowed_doc_ids

            cursor = conn.execute(query_sql, params)
            rows = cursor.fetchall()

            for row in rows:
                chk_id = row["chunk_id"]
                blob = row["vector_blob"]
                dim = row["dimension"]
                vec = list(struct.unpack(f"{dim}f", blob))
                score = cosine_similarity(query_vector, vec)
                results.append((chk_id, score))

            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]
        except Exception as e:
            logger.error(f"SQLiteVectorStore search_vectors error: {e}")
            return []
        finally:
            conn.close()

    def delete_vectors(self, chunk_ids: List[str]) -> bool:
        if not chunk_ids:
            return True
        conn = self._get_connection()
        try:
            with conn:
                placeholders = ",".join(["?"] * len(chunk_ids))
                conn.execute(f"DELETE FROM knowledge_vectors WHERE chunk_id IN ({placeholders})", chunk_ids)
            return True
        except Exception as e:
            logger.error(f"SQLiteVectorStore delete_vectors error: {e}")
            return False
        finally:
            conn.close()

    def delete_document_vectors(self, document_id: str) -> bool:
        conn = self._get_connection()
        try:
            with conn:
                conn.execute("DELETE FROM knowledge_vectors WHERE document_id = ?", (document_id,))
            return True
        except Exception as e:
            logger.error(f"SQLiteVectorStore delete_document_vectors error: {e}")
            return False
        finally:
            conn.close()
