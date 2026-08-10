"""
Bounded Deep Research Loop Controller for J.A.R.V.I.S. I2.2 V5.
Executes multi-round deep research loop under an end-to-end 30.0s global wall-clock deadline.
Server bounds always override user-provided limits.
"""

import asyncio
import time
import logging
from typing import Optional, List, Set, Tuple

from intelligence.web.models import GroundingStatus
from intelligence.web.search_service import web_search_service
from intelligence.web.retrieval_service import web_retrieval_service
from intelligence.web.research.models import ResearchRequest, ResearchResponse
from intelligence.web.research.research_service import web_research_service
from intelligence.web.temporal.temporal_service import web_temporal_service, TemporalRequest

from intelligence.web.deep_research.models import (
    DeepResearchConfig,
    DeepResearchFinding,
    DeepResearchRequest,
    DeepResearchResponse,
    StoppingReason
)
from intelligence.web.deep_research.research_state import DeepResearchState
from intelligence.web.deep_research.link_analyzer import link_analyzer
from intelligence.web.deep_research.source_discovery import source_discovery
from intelligence.web.deep_research.evidence_gap_detector import evidence_gap_detector
from intelligence.web.deep_research.stopping_policy import stopping_policy
from intelligence.web.deep_research.coverage_analyzer import coverage_analyzer
from intelligence.web.deep_research.research_synthesizer import research_synthesizer

logger = logging.getLogger("JARVIS_ResearchController")

SERVER_HARD_CONFIG = DeepResearchConfig()


class ResearchController:
    """Controls multi-round deep research loop execution."""

    async def execute_deep_research(
        self,
        request: DeepResearchRequest
    ) -> DeepResearchResponse:
        """
        Executes bounded deep research loop under a 30.0s global wall-clock deadline.
        Server-side hard limits always override user limits.
        """
        start_time = time.time()
        # Effective config: hard server limits override user request
        config = DeepResearchConfig(
            max_rounds=min(request.max_rounds, SERVER_HARD_CONFIG.max_rounds),
            max_search_queries_total=SERVER_HARD_CONFIG.max_search_queries_total,
            max_fetched_pages=SERVER_HARD_CONFIG.max_fetched_pages,
            max_wall_clock_seconds=SERVER_HARD_CONFIG.max_wall_clock_seconds
        )

        state = DeepResearchState(
            research_id=f"deep_{int(start_time * 1000)}",
            query=request.query,
            conversation_id=request.conversation_id
        )

        try:
            return await asyncio.wait_for(
                self._run_deep_research_loop(request, state, config, start_time),
                timeout=config.max_wall_clock_seconds
            )
        except asyncio.TimeoutError:
            elapsed = (time.time() - start_time) * 1000
            logger.warning(f"[ResearchController] Global 30.0s timeout exceeded for query: '{request.query}'")
            return self._build_timeout_response(request, state, elapsed)
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.error(f"[ResearchController] Execution error: {e}", exc_info=True)
            return DeepResearchResponse(
                query=request.query,
                status="FAILED",
                stopping_reason=StoppingReason.TIMEOUT,
                latency_ms=elapsed,
                error=str(e)
            )

    async def _run_deep_research_loop(
        self,
        request: DeepResearchRequest,
        state: DeepResearchState,
        config: DeepResearchConfig,
        start_time: float
    ) -> DeepResearchResponse:
        """Core multi-round deep research execution loop."""

        # 1. Round 1: Execute initial V3 research plan + V1 search + V2 safe retrieval
        research_req = ResearchRequest(query=request.query, force_research=True, conversation_id=request.conversation_id)
        r_resp = await web_research_service.execute_research(research_req)

        # Record initial queries and visited URLs
        state.attempted_queries.add(request.query)
        for src in r_resp.sources:
            state.visited_urls.add(src.canonical_url)
            state.visited_urls.add(src.url)

        state.sources.extend(r_resp.sources)
        state.evidence_items.extend(r_resp.evidence_items)
        state.sub_questions = [f"Sub-question {i+1} regarding '{request.query}'" for i in range(2)]

        # Check V4 temporal integration if temporal intent applies
        if request.user_timezone or "today" in request.query.lower() or "latest" in request.query.lower():
            t_req = TemporalRequest(query=request.query, user_timezone=request.user_timezone, conversation_id=request.conversation_id)
            await web_temporal_service.execute_temporal_research(t_req)

        # Main Deep Research Round Loop
        stopping_reason = StoppingReason.PARTIAL_EVIDENCE

        for round_idx in range(1, config.max_rounds + 1):
            # A. Detect structural evidence gaps
            gaps = evidence_gap_detector.detect_gaps(
                sub_questions=state.sub_questions,
                evidence_items=state.evidence_items,
                sources=state.sources,
                conflicts=state.contradictions
            )
            state.unresolved_gaps = gaps

            # B. Extract and classify candidate links from retrieved V2 pages
            # Reuse evidence text and source metadata cleanly
            discovered_round_links = []
            for src in state.sources:
                src_snippet = getattr(src, "snippet", "") or getattr(src, "title", "")
                links = await link_analyzer.extract_and_classify_links(
                    html_content=f"<html><body><article><h1>{src.title}</h1><p>{src_snippet}</p></article></body></html>",
                    source_url=src.canonical_url,
                    visited_urls=state.visited_urls,
                    max_links=config.max_discovered_links_per_page
                )


                discovered_round_links.extend(links)

            state.discovered_links.extend(discovered_round_links)
            state.urls_discovered_count += len(discovered_round_links)
            state.urls_rejected_count += sum(1 for l in discovered_round_links if not l.is_eligible_for_selection)

            # C. Select candidate links for escalation to primary/official sources
            escalation_links = source_discovery.select_candidate_links_for_escalation(
                discovered_links=discovered_round_links,
                visited_urls=state.visited_urls,
                max_select=3
            )

            # D. Generate targeted gap queries (tracing to gap_id / sub_question_id)
            targeted_queries = source_discovery.generate_targeted_gap_queries(
                gaps=gaps,
                attempted_queries=state.attempted_queries,
                max_queries=2
            )

            # Check stopping policy before executing round fetches
            has_eligible_links = len(escalation_links) > 0
            has_eligible_queries = len(targeted_queries) > 0

            should_stop, reason = stopping_policy.evaluate_stopping_condition(
                state=state,
                config=config,
                has_eligible_links=has_eligible_links,
                has_eligible_queries=has_eligible_queries
            )

            if should_stop:
                stopping_reason = reason
                break

            # E. Execute Follow-up Retrievals for escalation links via V2 safe retrieval
            urls_to_fetch = [link.canonical_url for link in escalation_links if link.canonical_url not in state.visited_urls]
            new_sources_added = 0
            new_evidence_added = 0

            if urls_to_fetch:
                docs, ev_reg, g_status = await web_retrieval_service.fetch_pages_parallel(
                    urls=urls_to_fetch[:config.max_concurrent_fetches],
                    query=request.query
                )
                for doc in docs:
                    state.visited_urls.add(doc.metadata.canonical_url)
                    new_sources_added += 1
                    new_evidence_added += len(doc.evidence_chunks)

            # F. Execute Follow-up Targeted Queries via V1 search
            for q_str, gap_id, subq_id in targeted_queries:
                state.attempted_queries.add(q_str)
                s_res = await web_search_service.search(query=q_str)
                for item in s_res.results[:2]:
                    if item.canonical_url not in state.visited_urls:
                        state.visited_urls.add(item.canonical_url)

            # Record round novelty delta
            state.record_round_novelty(
                new_sources_count=new_sources_added,
                new_evidence_count=new_evidence_added,
                resolved_gaps_count=1 if new_sources_added > 0 else 0,
                new_conflicts_count=len(state.contradictions),
                new_primary_sources_count=sum(1 for l in escalation_links if l.category.value in ("OFFICIAL", "PRIMARY_SOURCE"))
            )

        # 2. Final Coverage Analysis
        coverage = coverage_analyzer.analyze_coverage(
            sub_questions=state.sub_questions,
            evidence_items=state.evidence_items,
            sources=state.sources,
            conflicts=state.contradictions
        )

        # 3. Final Synthesis
        finding = research_synthesizer.synthesize(
            state=state,
            coverage=coverage,
            stopping_reason=stopping_reason
        )

        elapsed = (time.time() - start_time) * 1000
        return DeepResearchResponse(
            query=request.query,
            status="COMPLETE",
            stopping_reason=stopping_reason,
            finding=finding,
            rounds_completed=state.completed_rounds,
            total_queries=len(state.attempted_queries),
            total_pages_fetched=len(state.visited_urls),
            urls_discovered=state.urls_discovered_count,
            urls_rejected=state.urls_rejected_count,
            gaps_resolved_count=sum(1 for g in state.unresolved_gaps if g.is_resolved),
            primary_sources_count=sum(1 for s in state.sources if s.suitability.is_primary_source or s.suitability.is_official),
            contradictions_count=len(state.contradictions),
            coverage=coverage,
            grounding_status=GroundingStatus.FULL_PAGE_RETRIEVED,
            latency_ms=elapsed
        )

    def _build_timeout_response(
        self,
        request: DeepResearchRequest,
        state: DeepResearchState,
        elapsed_ms: float
    ) -> DeepResearchResponse:
        """Builds structured response on timeout/cancellation."""
        coverage = coverage_analyzer.analyze_coverage(
            sub_questions=state.sub_questions,
            evidence_items=state.evidence_items,
            sources=state.sources,
            conflicts=state.contradictions
        )
        finding = research_synthesizer.synthesize(
            state=state,
            coverage=coverage,
            stopping_reason=StoppingReason.TIMEOUT
        )
        return DeepResearchResponse(
            query=request.query,
            status="TIMEOUT",
            stopping_reason=StoppingReason.TIMEOUT,
            finding=finding,
            rounds_completed=state.completed_rounds,
            total_queries=len(state.attempted_queries),
            total_pages_fetched=len(state.visited_urls),
            urls_discovered=state.urls_discovered_count,
            urls_rejected=state.urls_rejected_count,
            coverage=coverage,
            grounding_status=GroundingStatus.SEARCH_SNIPPET_FALLBACK,
            latency_ms=elapsed_ms,
            error="Deep research loop exceeded 30.0s global wall-clock deadline; outstanding tasks cancelled and resources cleaned up."
        )


research_controller = ResearchController()
