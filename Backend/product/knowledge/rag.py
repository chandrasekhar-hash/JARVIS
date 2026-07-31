"""
JARVIS Product 1.6 - RAG Subsystem.
Implements RAGCoordinator, ContextBuilder, and HallucinationGuard.
"""

import logging
from typing import List, Dict, Any, Optional
from .retrieval import RetrievalPipeline

logger = logging.getLogger(__name__)


class ContextBuilder:
    @staticmethod
    def build_context_prompt(
        query: str,
        retrieved_results: List[Dict[str, Any]],
        max_tokens: int = 3000,
    ) -> Tuple_Prompt_Context:
        """
        Assembles bounded context snippets with exact markdown citation headers.
        """
        context_blocks = []
        token_estimate = 0

        for item in retrieved_results:
            snippet = (
                f"--- CONTEXT SNIPPET ---\n"
                f"Citation: {item['citation']}\n"
                f"Document: {item['document_title']}\n"
                f"Content:\n{item['text']}\n"
            )
            est_tokens = len(snippet) // 4
            if token_estimate + est_tokens > max_tokens:
                break
            context_blocks.append(snippet)
            token_estimate += est_tokens

        formatted_context = "\n".join(context_blocks)
        system_prompt = (
            "You are JARVIS, an intelligent AI assistant. "
            "Answer the user query strictly based on the provided Knowledge Context snippets. "
            "Include inline bracket citations for every factual statement.\n\n"
            f"KNOWLEDGE CONTEXT:\n{formatted_context}\n\n"
            f"USER QUERY:\n{query}"
        )
        return system_prompt, formatted_context


Tuple_Prompt_Context = tuple[str, str]


class HallucinationGuard:
    @staticmethod
    def verify_groundedness(response_text: str, context_text: str) -> Dict[str, Any]:
        """
        Verifies that answer terms are grounded within retrieved context.
        """
        if not response_text or not context_text:
            return {"is_grounded": True, "confidence": 1.0}

        resp_words = set(response_text.lower().split())
        ctx_words = set(context_text.lower().split())

        # Ignore common stop words
        stop_words = {"the", "a", "an", "is", "are", "and", "or", "in", "on", "at", "to", "for", "of", "with", "this", "that"}
        resp_content_words = resp_words - stop_words
        if not resp_content_words:
            return {"is_grounded": True, "confidence": 1.0}

        overlap = len(resp_content_words.intersection(ctx_words))
        ratio = overlap / max(1, len(resp_content_words))

        is_grounded = ratio >= 0.30
        return {
            "is_grounded": is_grounded,
            "grounding_ratio": round(ratio, 2),
            "unsupported_flag": not is_grounded,
        }


class RAGCoordinator:
    def __init__(self, retrieval_pipeline: RetrievalPipeline):
        self.retrieval_pipeline = retrieval_pipeline
        self.context_builder = ContextBuilder()
        self.hallucination_guard = HallucinationGuard()

    def query(
        self,
        user_query: str,
        user_id: str,
        top_k: int = 5,
        max_context_tokens: int = 3000,
        user_roles: Optional[List[str]] = None,
        plugin_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        retrieved_results = self.retrieval_pipeline.retrieve(
            query=user_query,
            user_id=user_id,
            top_k=top_k,
            user_roles=user_roles,
            plugin_id=plugin_id,
        )

        if not retrieved_results:
            return {
                "answer": "I could not find any relevant information in your knowledge base to answer this question.",
                "citations": [],
                "context_used": "",
                "is_grounded": True,
                "retrieved_count": 0,
            }

        prompt, context_str = self.context_builder.build_context_prompt(
            query=user_query,
            retrieved_results=retrieved_results,
            max_tokens=max_context_tokens,
        )

        citations = [item["citation"] for item in retrieved_results]

        return {
            "prompt": prompt,
            "citations": citations,
            "context_snippets": retrieved_results,
            "context_used": context_str,
            "retrieved_count": len(retrieved_results),
        }
