"""
JARVIS Product 1.6 - Knowledge Engine Tool Registrations for P1.5 Tool Execution Engine.
Registers knowledge tools (`knowledge_ingest`, `knowledge_search`, `knowledge_query_rag`, `knowledge_delete`, `knowledge_reindex`).
"""

import logging
from typing import Dict, Any, List
from ...tools.models import ToolMetadata, ToolCategory, ToolCapability
from ..knowledge_engine import knowledge_manager_instance

logger = logging.getLogger(__name__)


def handle_knowledge_ingest(file_path: str, title: str, user_id: str = "default_user", tags: List[str] = None) -> Dict[str, Any]:
    doc = knowledge_manager_instance.ingest_document(
        file_path=file_path,
        title=title,
        owner_id=user_id,
        tags=tags,
    )
    return {
        "status": "success",
        "document_id": doc.document_id,
        "title": doc.title,
        "total_chunks": doc.total_chunks,
        "checksum": doc.checksum,
    }


def handle_knowledge_search(query: str, user_id: str = "default_user", top_k: int = 5) -> Dict[str, Any]:
    results = knowledge_manager_instance.search_knowledge(
        query=query,
        user_id=user_id,
        top_k=top_k,
    )
    return {
        "status": "success",
        "query": query,
        "results_count": len(results),
        "results": results,
    }


def handle_knowledge_query_rag(query: str, user_id: str = "default_user", top_k: int = 5) -> Dict[str, Any]:
    rag_payload = knowledge_manager_instance.query_rag(
        user_query=query,
        user_id=user_id,
        top_k=top_k,
    )
    return {
        "status": "success",
        "rag_payload": rag_payload,
    }


def handle_knowledge_delete(document_id: str, user_id: str = "default_user") -> Dict[str, Any]:
    success = knowledge_manager_instance.delete_document(document_id=document_id, user_id=user_id)
    return {
        "status": "success" if success else "failed",
        "document_id": document_id,
        "deleted": success,
    }


def handle_knowledge_reindex(document_id: str, user_id: str = "default_user") -> Dict[str, Any]:
    success = knowledge_manager_instance.reindex_document(document_id=document_id, user_id=user_id)
    return {
        "status": "success" if success else "failed",
        "document_id": document_id,
        "reindexed": success,
    }


def get_knowledge_tool_metadatas() -> List[ToolMetadata]:
    return [
        ToolMetadata(
            tool_id="knowledge_ingest",
            name="Ingest Knowledge Document",
            description="Ingests a PDF, Word document, text, Markdown, HTML, or image file into the JARVIS Knowledge Engine.",
            category=ToolCategory.INFORMATION,
            capabilities=[ToolCapability.FILESYSTEM_READ.value],
            safety_level="safe",
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "title": {"type": "string"},
                    "user_id": {"type": "string", "default": "default_user"},
                },
                "required": ["file_path", "title"],
            },
            handler=handle_knowledge_ingest,
        ),
        ToolMetadata(
            tool_id="knowledge_search",
            name="Search Knowledge Base",
            description="Performs hybrid semantic and keyword search across ingested user knowledge documents.",
            category=ToolCategory.INFORMATION,
            capabilities=[ToolCapability.READ_ONLY.value],
            safety_level="safe",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "user_id": {"type": "string", "default": "default_user"},
                    "top_k": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
            handler=handle_knowledge_search,
        ),
        ToolMetadata(
            tool_id="knowledge_query_rag",
            name="Query RAG Knowledge",
            description="Retrieves pertinent knowledge chunks and builds a grounded prompt context for answering user questions.",
            category=ToolCategory.INFORMATION,
            capabilities=[ToolCapability.READ_ONLY.value],
            safety_level="safe",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "user_id": {"type": "string", "default": "default_user"},
                    "top_k": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
            handler=handle_knowledge_query_rag,
        ),
        ToolMetadata(
            tool_id="knowledge_delete",
            name="Delete Knowledge Document",
            description="Deletes a knowledge document and all its corresponding chunk vectors from the index.",
            category=ToolCategory.UTILITY,
            capabilities=[ToolCapability.FILESYSTEM_WRITE.value],
            safety_level="confirmation_required",
            input_schema={
                "type": "object",
                "properties": {
                    "document_id": {"type": "string"},
                    "user_id": {"type": "string", "default": "default_user"},
                },
                "required": ["document_id"],
            },
            handler=handle_knowledge_delete,
        ),
        ToolMetadata(
            tool_id="knowledge_reindex",
            name="Re-Index Knowledge Document",
            description="Re-parses, re-chunks, and re-embeds a document within the Knowledge Engine.",
            category=ToolCategory.UTILITY,
            capabilities=[ToolCapability.FILESYSTEM_WRITE.value],
            safety_level="confirmation_required",
            input_schema={
                "type": "object",
                "properties": {
                    "document_id": {"type": "string"},
                    "user_id": {"type": "string", "default": "default_user"},
                },
                "required": ["document_id"],
            },
            handler=handle_knowledge_reindex,
        ),
    ]
