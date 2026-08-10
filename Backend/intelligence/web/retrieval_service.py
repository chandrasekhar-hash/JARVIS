"""
Web Retrieval Service and Evidence Management Orchestrator for J.A.R.V.I.S. I2.2 V2.

Orchestrates URL safety validation, parallel fetching (bounded concurrency), content extraction,
evidence chunking, query-aware relevance selection, evidence source registry management (source_1, source_2),
untrusted prompt-injection boundary formatting, and programmatic source provenance resolution.
"""
import time
import re
import urllib.parse
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple


import config
from intelligence.web.models import (
    WebPageRequest,
    WebPageDocument,
    WebPageMetadata,
    WebRetrievalResponse,
    WebRetrievalStatus,
    EvidenceChunk,
    EvidenceRegistry,
    GroundingStatus,
    WebContentBlock,
    WebPageBlockType,
)
from intelligence.web.fetcher import web_fetcher
from intelligence.web.content_extractor import content_extractor
from tools.telemetry import log_structured, backend_log

logger = logging.getLogger("JARVIS_WebRetrievalService")


class EvidenceChunker:
    """
    Partitions structured document blocks into bounded evidence chunks
    preserving heading context, code block integrity, and source provenance.
    """

    @staticmethod
    def chunk_document(
        doc: WebPageDocument,
        source_id: str,
        target_chunk_chars: int = 1000
    ) -> List[EvidenceChunk]:
        """Partitions document blocks into evidence chunks respecting structural boundaries."""
        if not doc.blocks:
            return []

        chunks: List[EvidenceChunk] = []
        current_text_parts: List[str] = []
        current_blocks: List[int] = []
        current_heading_path: List[str] = []
        current_char_count = 0
        chunk_idx = 1

        for b in doc.blocks:
            # Code blocks and Tables should remain undivided in dedicated chunks if possible
            if b.block_type in (WebPageBlockType.CODE, WebPageBlockType.TABLE) and len(b.text) > 300:
                # Flush previous accumulated text
                if current_text_parts:
                    chunks.append(EvidenceChunk(
                        source_id=source_id,
                        source_url=doc.metadata.canonical_url,
                        chunk_index=chunk_idx,
                        heading_path=list(current_heading_path),
                        block_range=list(current_blocks),
                        text="\n\n".join(current_text_parts),
                        relevance_score=0.0
                    ))
                    chunk_idx += 1
                    current_text_parts = []
                    current_blocks = []
                    current_char_count = 0

                # Dedicated chunk for Code or Table
                chunks.append(EvidenceChunk(
                    source_id=source_id,
                    source_url=doc.metadata.canonical_url,
                    chunk_index=chunk_idx,
                    heading_path=list(b.heading_path),
                    block_range=[b.block_index],
                    text=b.text,
                    relevance_score=0.0
                ))
                chunk_idx += 1
                continue

            # Update heading context
            if b.heading_path:
                current_heading_path = b.heading_path

            current_text_parts.append(b.text)
            current_blocks.append(b.block_index)
            current_char_count += len(b.text)

            if current_char_count >= target_chunk_chars:
                chunks.append(EvidenceChunk(
                    source_id=source_id,
                    source_url=doc.metadata.canonical_url,
                    chunk_index=chunk_idx,
                    heading_path=list(current_heading_path),
                    block_range=list(current_blocks),
                    text="\n\n".join(current_text_parts),
                    relevance_score=0.0
                ))
                chunk_idx += 1
                current_text_parts = []
                current_blocks = []
                current_char_count = 0

        # Flush remaining blocks
        if current_text_parts:
            chunks.append(EvidenceChunk(
                source_id=source_id,
                source_url=doc.metadata.canonical_url,
                chunk_index=chunk_idx,
                heading_path=list(current_heading_path),
                block_range=list(current_blocks),
                text="\n\n".join(current_text_parts),
                relevance_score=0.0
            ))

        return chunks


class EvidenceSelector:
    """
    Ranks evidence chunks locally against user query using deterministic token overlap
    and heading matching algorithm without additional LLM calls.
    """

    @staticmethod
    def rank_chunks(chunks: List[EvidenceChunk], query: str, top_k: int = 5) -> List[EvidenceChunk]:
        """Scores chunks against query tokens and returns top_k relevant evidence chunks."""
        if not chunks or not query or not query.strip():
            return chunks[:top_k]

        # Tokenize query
        query_words = set(re.findall(r"\w+", query.lower()))
        stop_words = {"what", "is", "the", "in", "and", "or", "to", "a", "an", "of", "for", "with", "how", "on", "latest", "new"}
        meaningful_tokens = query_words - stop_words

        if not meaningful_tokens:
            meaningful_tokens = query_words

        for chunk in chunks:
            score = 0.0
            chunk_text_lower = chunk.text.lower()
            heading_text_lower = " ".join(chunk.heading_path).lower()

            # Token overlap score
            for token in meaningful_tokens:
                if token in chunk_text_lower:
                    score += 1.0
                if token in heading_text_lower:
                    score += 2.0  # Heading match boost

            # Code/table keyword boost if query asks for technical info
            if "code" in query_words or "example" in query_words or "function" in query_words:
                if "def " in chunk_text_lower or "class " in chunk_text_lower or "import " in chunk_text_lower:
                    score += 3.0

            chunk.relevance_score = score

        # Sort descending by relevance score
        sorted_chunks = sorted(chunks, key=lambda c: c.relevance_score, reverse=True)
        return sorted_chunks[:top_k]


class WebRetrievalService:
    """
    Main orchestrator for Webpage Retrieval & Content Intelligence (I2.2 V2).
    Exposes async single page fetch and parallel bounded multi-page retrieval methods.
    """

    def __init__(self):
        self.fetcher = web_fetcher
        self.extractor = content_extractor
        self.chunker = EvidenceChunker()
        self.selector = EvidenceSelector()

    async def fetch_page(self, request: WebPageRequest) -> WebRetrievalResponse:
        """
        Executes single page retrieval pipeline: fetch -> extract -> chunk -> score.
        """
        start_time = time.perf_counter()

        status, metadata, content_bytes, error_msg = await self.fetcher.fetch_page(
            url=request.url,
            timeout_seconds=request.timeout_seconds
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        if status != WebRetrievalStatus.SUCCESS or not metadata:
            # Create stub document for failed status
            dummy_meta = metadata or WebPageMetadata(
                requested_url=request.url,
                final_url=request.url,
                canonical_url=request.url,
                domain=urllib.parse.urlparse(request.url).netloc or "unknown",
                retrieved_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            )
            stub_doc = WebPageDocument(
                metadata=dummy_meta,
                blocks=[],
                extracted_text="",
                retrieval_status=status,
                warnings=[error_msg] if error_msg else [f"Retrieval ended with status: {status.value}"]
            )
            return WebRetrievalResponse(
                success=False,
                document=stub_doc,
                evidence_registry={},
                error=error_msg or f"Retrieval failed with status {status.value}",
                latency_ms=round(elapsed_ms, 2)
            )

        # Extract structured document
        document = self.extractor.parse_document(
            raw_bytes=content_bytes,
            initial_meta=metadata,
            max_content_chars=request.max_content_chars
        )

        source_id = "source_1"
        evidence_registry = {
            source_id: {
                "canonical_url": metadata.canonical_url,
                "requested_url": metadata.requested_url,
                "domain": metadata.domain,
                "title": metadata.title or metadata.domain,
                "retrieved_at": metadata.retrieved_at,
            }
        }

        # Chunk & Rank if query provided
        all_chunks = self.chunker.chunk_document(document, source_id=source_id)
        if request.query:
            selected_chunks = self.selector.rank_chunks(all_chunks, query=request.query, top_k=5)
        else:
            selected_chunks = all_chunks[:5]

        document.evidence_chunks = selected_chunks

        return WebRetrievalResponse(
            success=document.retrieval_status == WebRetrievalStatus.SUCCESS,
            document=document,
            evidence_registry=evidence_registry,
            latency_ms=round(elapsed_ms, 2)
        )

    async def fetch_pages_parallel(
        self,
        urls: List[str],
        query: Optional[str] = None,
        max_pages: Optional[int] = None
    ) -> Tuple[List[WebPageDocument], EvidenceRegistry, GroundingStatus]:
        """
        Fetches top N urls in parallel with bounded concurrency (asyncio.Semaphore(WEB_FETCH_CONCURRENCY)).
        Builds source evidence registry (source_1, source_2, ...) and ranks evidence chunks.
        """
        if not urls:
            return [], EvidenceRegistry(sources={}), GroundingStatus.SEARCH_SNIPPET_FALLBACK

        concurrency_limit = getattr(config, "WEB_FETCH_CONCURRENCY", 3)
        max_pages_limit = max_pages or getattr(config, "WEB_FETCH_MAX_PAGES", 3)
        target_urls = urls[:max_pages_limit]

        semaphore = asyncio.Semaphore(concurrency_limit)

        async def _bounded_fetch(url_str: str) -> WebRetrievalResponse:
            async with semaphore:
                req = WebPageRequest(url=url_str, query=query)
                return await self.fetch_page(req)

        tasks = [_bounded_fetch(u) for u in target_urls]
        responses: List[WebRetrievalResponse] = await asyncio.gather(*tasks, return_exceptions=True)

        documents: List[WebPageDocument] = []
        registry_sources: Dict[str, Dict[str, Any]] = {}
        source_idx = 1
        successful_retrievals = 0

        for idx, res in enumerate(responses):
            if isinstance(res, WebRetrievalResponse) and res.success and res.document:
                doc = res.document
                src_id = f"source_{source_idx}"
                doc.metadata.canonical_url = doc.metadata.canonical_url or target_urls[idx]

                # Update chunks with unified source_id
                rebound_chunks = self.chunker.chunk_document(doc, source_id=src_id)
                if query:
                    selected_chunks = self.selector.rank_chunks(rebound_chunks, query=query, top_k=3)
                else:
                    selected_chunks = rebound_chunks[:3]
                doc.evidence_chunks = selected_chunks

                documents.append(doc)
                registry_sources[src_id] = {
                    "canonical_url": doc.metadata.canonical_url,
                    "requested_url": doc.metadata.requested_url,
                    "domain": doc.metadata.domain,
                    "title": doc.metadata.title or doc.metadata.domain,
                    "retrieved_at": doc.metadata.retrieved_at,
                }
                source_idx += 1
                successful_retrievals += 1
            elif isinstance(res, WebRetrievalResponse) and res.document:
                documents.append(res.document)

        grounding_status = (
            GroundingStatus.FULL_PAGE_RETRIEVED
            if successful_retrievals > 0
            else GroundingStatus.SEARCH_SNIPPET_FALLBACK
        )

        return documents, EvidenceRegistry(sources=registry_sources), grounding_status

    @staticmethod
    def format_untrusted_evidence_block(documents: List[WebPageDocument], registry: EvidenceRegistry) -> str:
        """
        Formats evidence chunks into untrusted external evidence blocks with source_id references
        to prevent prompt injection while preserving structure.
        """
        evidence_blocks = []

        for doc in documents:
            if doc.retrieval_status != WebRetrievalStatus.SUCCESS or not doc.evidence_chunks:
                continue

            for chunk in doc.evidence_chunks:
                heading_str = " > ".join(chunk.heading_path) if chunk.heading_path else "General Content"
                block_xml = (
                    f'<UNTRUSTED_WEBPAGE_CONTENT source_id="{chunk.source_id}" canonical="{chunk.source_url}">\n'
                    f"[Heading Context: {heading_str}]\n"
                    f"{chunk.text}\n"
                    f"</UNTRUSTED_WEBPAGE_CONTENT>"
                )
                evidence_blocks.append(block_xml)

        if not evidence_blocks:
            return ""

        # Format source registry map
        registry_lines = ["\nVERIFIED EVIDENCE SOURCE REGISTRY:"]
        for src_id, src_meta in registry.sources.items():
            registry_lines.append(f"- [{src_id}]: {src_meta['title']} ({src_meta['canonical_url']})")

        return "\n\n".join(evidence_blocks) + "\n" + "\n".join(registry_lines)

    @staticmethod
    def resolve_source_citations(response_text: str, registry: EvidenceRegistry) -> List[Dict[str, Any]]:
        """
        Programmatic Provenance Verification:
        Resolves source IDs (source_1, source_2) cited in the response_text to verified canonical URLs.
        Strips and rejects any unverified / model-invented source IDs.
        """
        if not response_text or not registry.sources:
            return []

        cited_ids = set(re.findall(r"\bsource_\d+\b", response_text))
        verified_sources: List[Dict[str, Any]] = []

        for src_id in sorted(cited_ids):
            if src_id in registry.sources:
                verified_sources.append({
                    "source_id": src_id,
                    "canonical_url": registry.sources[src_id]["canonical_url"],
                    "title": registry.sources[src_id]["title"],
                    "domain": registry.sources[src_id]["domain"],
                })

        return verified_sources


# Global singleton instance
web_retrieval_service = WebRetrievalService()
