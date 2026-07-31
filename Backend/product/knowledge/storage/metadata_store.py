"""
JARVIS Product 1.6 - SQLite Metadata Store & FTS5 Sparse Search Engine.
Manages relational storage for Documents, Chunks, ACLs, and Full-Text Search (FTS5).
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from ..interfaces import IMetadataStore
from ..models import (
    Document,
    Chunk,
    DocumentStatus,
    DocumentType,
    DocumentPermissions,
    ChunkLocation,
)

logger = logging.getLogger(__name__)


class SQLiteMetadataStore(IMetadataStore):
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
                # Documents Table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS knowledge_documents (
                        document_id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        owner TEXT NOT NULL,
                        source TEXT NOT NULL,
                        document_type TEXT NOT NULL,
                        language TEXT NOT NULL,
                        checksum TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        tags_json TEXT,
                        permissions_json TEXT,
                        embedding_version TEXT NOT NULL,
                        index_version TEXT NOT NULL,
                        status TEXT NOT NULL,
                        file_size_bytes INTEGER DEFAULT 0,
                        total_chunks INTEGER DEFAULT 0,
                        error_message TEXT,
                        custom_metadata_json TEXT
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_owner ON knowledge_documents(owner);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_checksum ON knowledge_documents(checksum);")

                # Chunks Table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS knowledge_chunks (
                        chunk_id TEXT PRIMARY KEY,
                        document_id TEXT NOT NULL,
                        chunk_index INTEGER NOT NULL,
                        text TEXT NOT NULL,
                        token_count INTEGER NOT NULL,
                        location_json TEXT,
                        checksum TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (document_id) REFERENCES knowledge_documents(document_id) ON DELETE CASCADE
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON knowledge_chunks(document_id);")

                # SQLite FTS5 Table for Sparse Keyword Search
                try:
                    conn.execute("""
                        CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts5 USING fts5(
                            chunk_id UNINDEXED,
                            document_id UNINDEXED,
                            text,
                            tokenize='porter unicode61'
                        )
                    """)
                except sqlite3.OperationalError as e:
                    logger.warning(f"FTS5 creation fallback notice: {e}")
        finally:
            conn.close()

    def save_document(self, document: Document) -> bool:
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO knowledge_documents (
                        document_id, title, owner, source, document_type, language, checksum,
                        created_at, updated_at, tags_json, permissions_json, embedding_version,
                        index_version, status, file_size_bytes, total_chunks, error_message, custom_metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document.document_id,
                        document.title,
                        document.owner,
                        document.source,
                        document.document_type.value,
                        document.language,
                        document.checksum,
                        document.created_at.isoformat(),
                        document.updated_at.isoformat(),
                        json.dumps(document.tags),
                        json.dumps(document.permissions.to_dict()),
                        document.embedding_version,
                        document.index_version,
                        document.status.value,
                        document.file_size_bytes,
                        document.total_chunks,
                        document.error_message,
                        json.dumps(document.custom_metadata),
                    ),
                )
            return True
        except Exception as e:
            logger.error(f"save_document error: {e}")
            return False
        finally:
            conn.close()

    def _row_to_document(self, row: sqlite3.Row) -> Document:
        tags = json.loads(row["tags_json"]) if row["tags_json"] else []
        perm_dict = json.loads(row["permissions_json"]) if row["permissions_json"] else {}
        custom_meta = json.loads(row["custom_metadata_json"]) if row["custom_metadata_json"] else {}
        return Document(
            document_id=row["document_id"],
            title=row["title"],
            owner=row["owner"],
            source=row["source"],
            document_type=DocumentType(row["document_type"]),
            language=row["language"],
            checksum=row["checksum"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            tags=tags,
            permissions=DocumentPermissions.from_dict(perm_dict),
            embedding_version=row["embedding_version"],
            index_version=row["index_version"],
            status=DocumentStatus(row["status"]),
            file_size_bytes=row["file_size_bytes"],
            total_chunks=row["total_chunks"],
            error_message=row["error_message"],
            custom_metadata=custom_meta,
        )

    def get_document(self, document_id: str) -> Optional[Document]:
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT * FROM knowledge_documents WHERE document_id = ?", (document_id,))
            row = cursor.fetchone()
            return self._row_to_document(row) if row else None
        finally:
            conn.close()

    def list_documents(
        self,
        owner_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Document]:
        conn = self._get_connection()
        try:
            if owner_id:
                cursor = conn.execute(
                    "SELECT * FROM knowledge_documents WHERE owner = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (owner_id, limit, offset),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM knowledge_documents ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                )
            rows = cursor.fetchall()
            return [self._row_to_document(r) for r in rows]
        finally:
            conn.close()

    def delete_document(self, document_id: str) -> bool:
        conn = self._get_connection()
        try:
            with conn:
                conn.execute("DELETE FROM knowledge_fts5 WHERE document_id = ?", (document_id,))
                conn.execute("DELETE FROM knowledge_chunks WHERE document_id = ?", (document_id,))
                conn.execute("DELETE FROM knowledge_documents WHERE document_id = ?", (document_id,))
            return True
        except Exception as e:
            logger.error(f"delete_document error: {e}")
            return False
        finally:
            conn.close()

    def save_chunks(self, chunks: List[Chunk]) -> bool:
        if not chunks:
            return True
        conn = self._get_connection()
        try:
            with conn:
                for chk in chunks:
                    loc_json = json.dumps(chk.location.to_dict()) if chk.location else "{}"
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO knowledge_chunks (
                            chunk_id, document_id, chunk_index, text, token_count, location_json, checksum, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            chk.chunk_id,
                            chk.document_id,
                            chk.chunk_index,
                            chk.text,
                            chk.token_count,
                            loc_json,
                            chk.checksum,
                            chk.created_at.isoformat(),
                        ),
                    )
                    # Populate FTS5 Index
                    try:
                        conn.execute(
                            "INSERT OR REPLACE INTO knowledge_fts5 (chunk_id, document_id, text) VALUES (?, ?, ?)",
                            (chk.chunk_id, chk.document_id, chk.text),
                        )
                    except sqlite3.OperationalError:
                        pass
            return True
        except Exception as e:
            logger.error(f"save_chunks error: {e}")
            return False
        finally:
            conn.close()

    def _row_to_chunk(self, row: sqlite3.Row) -> Chunk:
        loc_dict = json.loads(row["location_json"]) if row["location_json"] else {}
        return Chunk(
            chunk_id=row["chunk_id"],
            document_id=row["document_id"],
            chunk_index=row["chunk_index"],
            text=row["text"],
            token_count=row["token_count"],
            location=ChunkLocation.from_dict(loc_dict),
            checksum=row["checksum"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT * FROM knowledge_chunks WHERE chunk_id = ?", (chunk_id,))
            row = cursor.fetchone()
            return self._row_to_chunk(row) if row else None
        finally:
            conn.close()

    def get_chunks_by_document(self, document_id: str) -> List[Chunk]:
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM knowledge_chunks WHERE document_id = ? ORDER BY chunk_index ASC",
                (document_id,),
            )
            rows = cursor.fetchall()
            return [self._row_to_chunk(r) for r in rows]
        finally:
            conn.close()

    def get_chunks_by_ids(self, chunk_ids: List[str]) -> List[Chunk]:
        if not chunk_ids:
            return []
        conn = self._get_connection()
        try:
            placeholders = ",".join(["?"] * len(chunk_ids))
            cursor = conn.execute(f"SELECT * FROM knowledge_chunks WHERE chunk_id IN ({placeholders})", chunk_ids)
            rows = cursor.fetchall()
            return [self._row_to_chunk(r) for r in rows]
        finally:
            conn.close()

    def delete_chunks_by_document(self, document_id: str) -> bool:
        conn = self._get_connection()
        try:
            with conn:
                conn.execute("DELETE FROM knowledge_fts5 WHERE document_id = ?", (document_id,))
                conn.execute("DELETE FROM knowledge_chunks WHERE document_id = ?", (document_id,))
            return True
        except Exception as e:
            logger.error(f"delete_chunks_by_document error: {e}")
            return False
        finally:
            conn.close()

    def search_fts5_keywords(
        self,
        query: str,
        top_k: int = 10,
        allowed_doc_ids: Optional[List[str]] = None,
    ) -> List[Tuple[str, float]]:
        conn = self._get_connection()
        results: List[Tuple[str, float]] = []
        clean_q = "".join([c if c.isalnum() or c in (" ", "_") else " " for c in query]).strip()
        if not clean_q:
            return []

        try:
            params: List[Any] = [clean_q]
            filter_sql = ""
            if allowed_doc_ids is not None:
                if not allowed_doc_ids:
                    return []
                placeholders = ",".join(["?"] * len(allowed_doc_ids))
                filter_sql = f" AND document_id IN ({placeholders})"
                params.extend(allowed_doc_ids)

            params.append(top_k)
            sql = f"""
                SELECT chunk_id, bm25(knowledge_fts5) AS score
                FROM knowledge_fts5
                WHERE knowledge_fts5 MATCH ? {filter_sql}
                ORDER BY score ASC
                LIMIT ?
            """
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            for r in rows:
                # Convert BM25 score to positive similarity ranking
                bm25_val = abs(float(r["score"]))
                norm_score = 1.0 / (1.0 + bm25_val)
                results.append((r["chunk_id"], norm_score))
            return results
        except sqlite3.OperationalError as e:
            logger.warning(f"FTS5 search operational error fallback: {e}")
            # Simple LIKE fallback
            words = clean_q.split()
            if not words:
                return []
            like_clause = "%" + "%".join(words) + "%"
            sql = "SELECT chunk_id FROM knowledge_chunks WHERE text LIKE ? LIMIT ?"
            cursor = conn.execute(sql, [like_clause, top_k])
            rows = cursor.fetchall()
            return [(r["chunk_id"], 0.5) for r in rows]
        finally:
            conn.close()
