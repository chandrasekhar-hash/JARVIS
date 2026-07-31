"""
JARVIS Product 1.6 - Knowledge Engine Comprehensive Test Suite.
Tests Parsers, OCR, Chunking, Embeddings, Vector Storage, Metadata Store, Hybrid Search, RAG, Permissions, Deletion, and Tools.
"""

import os
import tempfile
import pytest
from backend.product.knowledge import (
    KnowledgeManager,
    DocumentManager,
    Document,
    DocumentStatus,
    DocumentType,
    DocumentPermissions,
    Chunk,
    ChunkingEngine,
    SQLiteVectorStore,
    SQLiteMetadataStore,
    HybridSearchEngine,
    RetrievalPipeline,
    RAGCoordinator,
    KnowledgePermissionEngine,
    get_knowledge_tool_metadatas,
)
from backend.product.knowledge.parsers import parser_factory


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def knowledge_mgr(temp_dir):
    db_path = os.path.join(temp_dir, "test_knowledge.db")
    mgr = KnowledgeManager(db_path=db_path)
    mgr.initialize()
    return mgr


def test_parsers_factory(temp_dir):
    txt_path = os.path.join(temp_dir, "sample.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("# Introduction\n\nJARVIS Knowledge Engine Product 1.6 test document content.")

    parser = parser_factory.get_parser(txt_path)
    text, meta = parser.parse(txt_path)
    assert "JARVIS Knowledge Engine" in text
    assert meta["char_count"] > 0


def test_chunking_engine():
    chunker = ChunkingEngine(default_chunk_size=20, default_overlap=5)
    sample_text = (
        "Paragraph one introduces the AI architecture.\n\n"
        "Paragraph two discusses vector database storage and indexing.\n\n"
        "Paragraph three covers retrieval augmented generation RAG workflows."
    )
    chunks = chunker.chunk_text("doc_123", sample_text, chunk_size=20, overlap=5)
    assert len(chunks) >= 2
    assert chunks[0].document_id == "doc_123"
    assert chunks[0].token_count > 0


def test_vector_and_metadata_store(temp_dir):
    db_path = os.path.join(temp_dir, "store_test.db")
    meta_store = SQLiteMetadataStore(db_path=db_path)
    vec_store = SQLiteVectorStore(db_path=db_path)
    meta_store.initialize()
    vec_store.initialize()

    doc = Document.create_new(
        title="Architecture Specification",
        owner="usr_alice",
        source="/tmp/arch.txt",
        document_type=DocumentType.TXT,
        checksum="sha256_mock_hash",
    )
    assert meta_store.save_document(doc) is True

    fetched_doc = meta_store.get_document(doc.document_id)
    assert fetched_doc is not None
    assert fetched_doc.title == "Architecture Specification"

    # Add Vectors & Chunks
    chk = Chunk.create_new(
        document_id=doc.document_id,
        chunk_index=0,
        text="JARVIS utilizes SQLite vector store for similarity search.",
        token_count=10,
        location=None,
        checksum="chk_sha256",
        embedding=[0.1] * 384,
    )
    assert meta_store.save_chunks([chk]) is True
    assert vec_store.add_vectors([chk.chunk_id], [[0.1] * 384], [{"document_id": doc.document_id}]) is True

    # Search Vectors
    results = vec_store.search_vectors([0.1] * 384, top_k=5)
    assert len(results) > 0
    assert results[0][0] == chk.chunk_id


def test_ingestion_and_search(knowledge_mgr, temp_dir):
    doc_path = os.path.join(temp_dir, "jarvis_guide.md")
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write("# JARVIS Product 1.6\n\nThe Knowledge Engine provides hybrid search and RAG capabilities.")

    doc = knowledge_mgr.ingest_document(
        file_path=doc_path,
        title="JARVIS Guide",
        owner_id="usr_bob",
        tags=["guide", "v1.6"],
    )

    assert doc.status == DocumentStatus.INDEXED
    assert doc.total_chunks > 0

    # Search Knowledge
    results = knowledge_mgr.search_knowledge("hybrid search RAG", user_id="usr_bob", top_k=5)
    assert len(results) > 0
    assert "JARVIS Guide" in results[0]["document_title"]


def test_rag_query(knowledge_mgr, temp_dir):
    doc_path = os.path.join(temp_dir, "memory_spec.txt")
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write("JARVIS stores user long-term episodic memory in SQLite relational tables with vector embeddings.")

    knowledge_mgr.ingest_document(
        file_path=doc_path,
        title="Memory Specification",
        owner_id="usr_alice",
    )

    rag_payload = knowledge_mgr.query_rag("Where does JARVIS store memory?", user_id="usr_alice")
    assert rag_payload["retrieved_count"] > 0
    assert len(rag_payload["citations"]) > 0
    assert "Memory Specification" in rag_payload["citations"][0]
    assert "SQLite" in rag_payload["context_used"]


def test_permission_isolation(knowledge_mgr, temp_dir):
    doc_path = os.path.join(temp_dir, "private_notes.txt")
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write("Confidential encryption keys and personal secrets.")

    # Alice ingests private doc
    knowledge_mgr.ingest_document(
        file_path=doc_path,
        title="Private Notes",
        owner_id="usr_alice",
    )

    # Bob searches -> Should receive 0 results
    bob_results = knowledge_mgr.search_knowledge("encryption keys", user_id="usr_bob")
    assert len(bob_results) == 0

    # Alice searches -> Should receive results
    alice_results = knowledge_mgr.search_knowledge("encryption keys", user_id="usr_alice")
    assert len(alice_results) > 0


def test_deletion_and_reindex(knowledge_mgr, temp_dir):
    doc_path = os.path.join(temp_dir, "temp_doc.txt")
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write("Temporary document for deletion and re-index testing.")

    doc = knowledge_mgr.ingest_document(
        file_path=doc_path,
        title="Temp Doc",
        owner_id="usr_alice",
    )

    # Reindex
    assert knowledge_mgr.reindex_document(doc.document_id, user_id="usr_alice") is True

    # Delete
    assert knowledge_mgr.delete_document(doc.document_id, user_id="usr_alice") is True
    assert knowledge_mgr.document_manager.get_document(doc.document_id) is None


def test_knowledge_tools_metadata():
    tools = get_knowledge_tool_metadatas()
    assert len(tools) == 5
    tool_ids = [t.tool_id for t in tools]
    assert "knowledge_ingest" in tool_ids
    assert "knowledge_search" in tool_ids
    assert "knowledge_query_rag" in tool_ids
    assert "knowledge_delete" in tool_ids
    assert "knowledge_reindex" in tool_ids
