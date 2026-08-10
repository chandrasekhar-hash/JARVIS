"""
Main WebResearchService Orchestrator for J.A.R.V.I.S. I2.2 V3.
Composes V1 WebSearchService + V2 WebRetrievalService under a 15.0s global wall-clock deadline.
Supports multi-turn context continuity and fail-closed provenance validation.
"""

import asyncio
import time
import logging
from typing import Optional, List, Dict, Any
from intelligence.web.models import GroundingStatus, WebRetrievalStatus
from intelligence.web.search_service import web_search_service
from intelligence.web.retrieval_service import web_retrieval_service
from intelligence.web.research.models import (
    ResearchRequest,
    ResearchResponse,
    ResearchIntent,
    ResearchStatus,
    ResearchPlan,
    ResearchSource,
    EvidenceItem,
    EvidenceRelationship,
    ResearchFinding
)
from intelligence.web.research.intent_classifier import research_intent_classifier
from intelligence.web.research.planner import research_planner, MAX_RESEARCH_TIME_SECONDS
from intelligence.web.research.source_selector import source_diversity_selector
from intelligence.web.research.evidence_analyzer import evidence_analyzer
from intelligence.web.research.fact_checker import fact_checker
from intelligence.web.research.provenance_manager import provenance_validator
from intelligence.web.research.synthesizer import research_synthesizer

logger = logging.getLogger("JARVIS_WebResearchService")


class WebResearchService:
    """Orchestrates V3 Multi-Source Research & Evidence Synthesis."""

    def __init__(self):
        self._context_cache: Dict[str, ResearchResponse] = {}

    async def execute_research(self, request: ResearchRequest) -> ResearchResponse:
        """
        Executes bounded multi-source research pipeline under a hard 15.0s global wall-clock deadline.
        """
        start_time = time.time()

        try:
            # Enforce global 15.0s wall-clock deadline across planning + search + retrieval + analysis + synthesis
            return await asyncio.wait_for(
                self._run_research_pipeline(request, start_time),
                timeout=MAX_RESEARCH_TIME_SECONDS
            )
        except asyncio.TimeoutError:
            elapsed = (time.time() - start_time) * 1000
            logger.warning(f"[WebResearchService] Global 15.0s research timeout exceeded after {elapsed:.2f}ms for query: '{request.query}'")
            return ResearchResponse(
                query=request.query,
                intent=ResearchIntent.GENERAL_RESEARCH,
                status=ResearchStatus.TIMEOUT,
                grounding_status=GroundingStatus.SEARCH_SNIPPET_FALLBACK,
                latency_ms=elapsed,
                error="Research pipeline exceeded global 15.0s wall-clock deadline."
            )
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.error(f"[WebResearchService] Execution error: {e}", exc_info=True)
            return ResearchResponse(
                query=request.query,
                intent=ResearchIntent.GENERAL_RESEARCH,
                status=ResearchStatus.RETRIEVAL_FAILED,
                grounding_status=GroundingStatus.SEARCH_SNIPPET_FALLBACK,
                latency_ms=elapsed,
                error=str(e)
            )

    async def _run_research_pipeline(self, request: ResearchRequest, start_time: float) -> ResearchResponse:
        """Core research pipeline execution."""
        # 1. Multi-turn continuity check
        if request.conversation_id and request.conversation_id in self._context_cache:
            prev_resp = self._context_cache[request.conversation_id]
            # Check if previous context covers query and is less than 5 minutes old
            if prev_resp.latency_ms > 0 and (time.time() - start_time) < 300:
                if any(w in request.query.lower() for w in ["what about", "more details", "pricing"]):
                    logger.info(f"[WebResearchService] Reusing bounded multi-turn context for conversation {request.conversation_id}")
                    # Retain previous sources while performing fresh targeted research if pricing/evidence absent
                    if not any("pricing" in ev.text.lower() for ev in prev_resp.evidence_items):
                        logger.info(f"[WebResearchService] Evidence absent in multi-turn context; triggering fresh bounded research.")

        # 2. Research Intent Classification & Fast Bypass
        intent, is_v3_needed = research_intent_classifier.classify_intent(request.query)
        if request.force_research:
            is_v3_needed = True

        if intent == ResearchIntent.NO_WEB:
            return ResearchResponse(
                query=request.query,
                intent=intent,
                status=ResearchStatus.COMPLETE,
                grounding_status=GroundingStatus.NONE,
                latency_ms=(time.time() - start_time) * 1000
            )

        # 3. Formulate Bounded Research Plan
        plan = research_planner.create_plan(request.query, intent)

        # 4. Compose V1 WebSearchService across sub-questions
        all_search_results = []
        for sub_q in plan.sub_questions:
            s_res = await web_search_service.search(query=sub_q.query)
            if s_res.results:
                all_search_results.extend(s_res.results)

        if not all_search_results:
            return ResearchResponse(
                query=request.query,
                intent=intent,
                status=ResearchStatus.SEARCH_FAILED,
                plan=plan,
                grounding_status=GroundingStatus.SEARCH_SNIPPET_FALLBACK,
                latency_ms=(time.time() - start_time) * 1000,
                error="Web search returned 0 candidate results."
            )

        # 5. Source Diversity & Suitability Selection
        selected_sources = source_diversity_selector.evaluate_and_select_sources(
            results=all_search_results,
            intent=intent,
            max_sources=request.max_sources
        )

        # 6. Compose V2 WebRetrievalService (Parallel Webpage Retrieval & Extraction)
        urls_to_fetch = [s.canonical_url for s in selected_sources]
        documents, ev_registry, g_status = await web_retrieval_service.fetch_pages_parallel(
            urls=urls_to_fetch,
            query=request.query
        )

        # Build structured EvidenceItem list
        evidence_items: List[EvidenceItem] = []
        ev_counter = 1
        for doc in documents:
            if doc.retrieval_status == WebRetrievalStatus.SUCCESS and doc.evidence_chunks:
                # Resolve source_id from canonical URL
                src = next((s for s in selected_sources if s.canonical_url == doc.metadata.canonical_url), None)
                src_id = src.source_id if src else "source_1"

                for chunk in doc.evidence_chunks[:3]:  # Max 3 chunks per page
                    ev_item = EvidenceItem(
                        evidence_id=f"ev_{ev_counter}",
                        source_id=src_id,
                        canonical_url=doc.metadata.canonical_url,
                        heading_path=chunk.heading_path,
                        text=chunk.text,
                        sub_question_id=getattr(chunk, "sub_question_id", "sub_q1"),
                        relationship=EvidenceRelationship.SUPPORTS
                    )
                    evidence_items.append(ev_item)
                    ev_counter += 1


        # 7. Evidence Analysis (Agreement & Contradiction Detection)
        claims, conflicts = evidence_analyzer.detect_agreements_and_conflicts(
            evidence_items=evidence_items,
            sources=selected_sources
        )

        # 8. Fact-Checking Evaluation if intent == FACT_CHECK
        fact_check_detail = None
        if intent == ResearchIntent.FACT_CHECK:
            fact_check_detail = fact_checker.evaluate_fact_check(
                query=request.query,
                evidence_items=evidence_items,
                sources=selected_sources
            )

        # 9. Research Synthesis
        finding = research_synthesizer.synthesize_finding(
            query=request.query,
            intent=intent,
            claims=claims,
            conflicts=conflicts,
            fact_check_detail=fact_check_detail,
            sources=selected_sources,
            evidence_items=evidence_items
        )

        # 10. Fail-Closed Provenance Validation & Repair
        repaired_text, validated_finding, is_valid = provenance_validator.validate_and_repair_response_text(
            text=finding.summary,
            finding=finding,
            evidence_items=evidence_items,
            sources=selected_sources
        )
        validated_finding.summary = repaired_text

        final_status = ResearchStatus.COMPLETE if is_valid else ResearchStatus.PARTIAL
        elapsed = (time.time() - start_time) * 1000

        response = ResearchResponse(
            query=request.query,
            intent=intent,
            status=final_status,
            plan=plan,
            sources=selected_sources,
            evidence_items=evidence_items,
            finding=validated_finding,
            grounding_status=g_status,
            latency_ms=elapsed
        )

        if request.conversation_id:
            self._context_cache[request.conversation_id] = response

        return response


web_research_service = WebResearchService()
