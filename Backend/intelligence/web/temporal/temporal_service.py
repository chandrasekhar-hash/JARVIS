"""
Main WebTemporalService Orchestrator for J.A.R.V.I.S. I2.2 V4.
Composes V1 WebSearchService + V2 WebRetrievalService + V3 Research Engine under an 18.0s global wall-clock deadline.
Integrates time window resolution, primary announcement resolution, story clustering, update detection,
ephemeral TemporalSnapshotStore diffing, and timeline building.
"""

import asyncio
import time
import logging
from typing import Optional, List, Dict, Any
from intelligence.web.models import GroundingStatus
from intelligence.web.search_service import web_search_service
from intelligence.web.retrieval_service import web_retrieval_service
from intelligence.web.research.models import ResearchRequest, ResearchResponse, ResearchStatus
from intelligence.web.research.research_service import web_research_service

from intelligence.web.temporal.models import (
    TemporalRequest,
    TemporalResponse,
    TemporalIntent,
    TemporalWindow,
    TemporalFinding,
    TemporalClaim,
    TemporalMetadata
)
from intelligence.web.temporal.intent_classifier import temporal_intent_classifier
from intelligence.web.temporal.time_window_resolver import time_window_resolver
from intelligence.web.temporal.publication_time_resolver import publication_time_resolver
from intelligence.web.temporal.primary_announcement_resolver import primary_announcement_resolver
from intelligence.web.temporal.event_extractor import event_extractor
from intelligence.web.temporal.story_clusterer import story_clusterer
from intelligence.web.temporal.update_detector import update_detector
from intelligence.web.temporal.freshness_evaluator import freshness_evaluator
from intelligence.web.temporal.timeline_builder import timeline_builder
from intelligence.web.temporal.snapshot_store import temporal_snapshot_store
from intelligence.web.temporal.temporal_provenance import temporal_provenance_validator

logger = logging.getLogger("JARVIS_WebTemporalService")

MAX_TEMPORAL_RESEARCH_SECONDS = 18.0  # End-to-end global wall-clock deadline


class WebTemporalService:
    """Orchestrates V4 Current Events, News & Freshness Intelligence."""

    async def execute_temporal_research(
        self,
        request: TemporalRequest,
        session_timezone: Optional[str] = None
    ) -> TemporalResponse:
        """
        Executes bounded temporal research pipeline under an 18.0s global wall-clock deadline.
        """
        start_time = time.time()

        try:
            return await asyncio.wait_for(
                self._run_temporal_pipeline(request, session_timezone, start_time),
                timeout=MAX_TEMPORAL_RESEARCH_SECONDS
            )
        except asyncio.TimeoutError:
            elapsed = (time.time() - start_time) * 1000
            logger.warning(f"[WebTemporalService] Global 18.0s timeout exceeded after {elapsed:.2f}ms for query: '{request.query}'")
            return TemporalResponse(
                query=request.query,
                intent=TemporalIntent.LATEST,
                status="TIMEOUT",
                window=TemporalWindow(source_expression=request.query),
                grounding_status=GroundingStatus.SEARCH_SNIPPET_FALLBACK,
                latency_ms=elapsed,
                error="Temporal research pipeline exceeded global 18.0s wall-clock deadline."
            )
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.error(f"[WebTemporalService] Execution error: {e}", exc_info=True)
            return TemporalResponse(
                query=request.query,
                intent=TemporalIntent.LATEST,
                status="FAILED",
                window=TemporalWindow(source_expression=request.query),
                grounding_status=GroundingStatus.SEARCH_SNIPPET_FALLBACK,
                latency_ms=elapsed,
                error=str(e)
            )

    async def _run_temporal_pipeline(
        self,
        request: TemporalRequest,
        session_timezone: Optional[str],
        start_time: float
    ) -> TemporalResponse:
        """Core temporal pipeline execution."""
        # 1. Temporal Intent Classification
        intent, is_temporal = temporal_intent_classifier.classify_intent(request.query)
        if request.force_temporal:
            is_temporal = True

        if not is_temporal:
            return TemporalResponse(
                query=request.query,
                intent=TemporalIntent.NON_TEMPORAL,
                status="COMPLETE",
                window=TemporalWindow(source_expression=request.query),
                grounding_status=GroundingStatus.NONE,
                latency_ms=(time.time() - start_time) * 1000
            )

        # 2. Time Window Resolution (Precedence: Request TZ -> Session TZ -> None)
        window = time_window_resolver.resolve_time_window(
            query=request.query,
            intent=intent,
            request_timezone=request.user_timezone,
            session_timezone=session_timezone
        )

        # 3. Check Ephemeral TemporalSnapshotStore for since-last-check intent
        prev_snapshot = None
        if request.conversation_id:
            prev_snapshot = await temporal_snapshot_store.get_latest_snapshot(request.conversation_id)

        # 4. Compose V3 WebResearchService to perform bounded multi-source research
        research_req = ResearchRequest(query=request.query, force_research=True, conversation_id=request.conversation_id)
        r_resp = await web_research_service.execute_research(research_req)

        if not r_resp.sources:
            return TemporalResponse(
                query=request.query,
                intent=intent,
                status="FAILED",
                window=window,
                grounding_status=GroundingStatus.SEARCH_SNIPPET_FALLBACK,
                latency_ms=(time.time() - start_time) * 1000,
                error="Temporal search returned 0 verified sources."
            )

        # 5. Primary Announcement Resolution
        primary_source, secondary_sources = primary_announcement_resolver.resolve_primary_announcements(r_resp.sources)

        # 6. Event Extraction & Story Clustering
        news_events = event_extractor.extract_events(r_resp.evidence_items, r_resp.sources)
        clusters = story_clusterer.cluster_events(news_events, r_resp.sources, primary_source)

        # 7. Update & Old-News Resurfacing Detection
        clusters = update_detector.classify_and_detect_resurfacing(clusters, window)

        # 8. Timeline Intelligence Generation
        timeline = timeline_builder.build_timeline(news_events)

        # 9. Temporal Snapshot Diffing Engine
        canonical_urls = [s.canonical_url for s in r_resp.sources]
        diff_status, has_prior_baseline = temporal_snapshot_store.compute_diff_status(
            new_urls=canonical_urls,
            new_events=news_events,
            previous_snapshot=prev_snapshot
        )

        # 10. Temporal Claims & Provenance Validation
        temp_claims: List[TemporalClaim] = []
        for idx, ev in enumerate(news_events):
            t_claim = TemporalClaim(
                claim_id=f"t_claim_{idx + 1}",
                statement=ev.title,
                supporting_evidence_ids=ev.evidence_ids,
                temporal_metadata=ev.temporal_metadata
            )
            temp_claims.append(t_claim)

        v_claims, _ = temporal_provenance_validator.validate_temporal_provenance(
            temp_claims, r_resp.evidence_items, r_resp.sources
        )

        # Save snapshot for since-last-check continuity if conversation_id provided
        if request.conversation_id:
            await temporal_snapshot_store.save_snapshot(
                conversation_id=request.conversation_id,
                topic_fingerprint=request.query[:50],
                events=news_events,
                claims=v_claims,
                canonical_urls=canonical_urls,
                source_ids=[s.source_id for s in r_resp.sources]
            )

        # 11. Format Grounded Temporal Finding Summary
        summary_lines = [f"Temporal News Synthesis ({intent.value}, Window: {window.start_time or 'Any'} to {window.end_time or 'Now'} UTC):"]
        if not has_prior_baseline and intent == TemporalIntent.SINCE_LAST_CHECK:
            summary_lines.append("[Notice: No prior comparison baseline snapshot existed for this conversation; fresh temporal research performed.]")

        summary_lines.append(f"Diff Status: {diff_status.value}")
        if primary_source:
            summary_lines.append(f"Primary Announcement Source: [{primary_source.source_id}] {primary_source.title} ({primary_source.domain})")

        if clusters:
            summary_lines.append("\nStory Clusters & Events:")
            for cl in clusters:
                old_tag = " (OLD NEWS RESURFACED)" if cl.is_old_news_resurfacing else ""
                summary_lines.append(f"- Cluster: {cl.topic_title}{old_tag} ({len(cl.member_source_ids)} sources)")
                for e in cl.events[:2]:
                    summary_lines.append(f"  * [{e.update_category.value}] {e.title}")

        if timeline:
            summary_lines.append("\nTimeline of Events:")
            for t_item in timeline[:5]:
                summary_lines.append(f"- [{t_item.timestamp_str}] {t_item.summary}")

        summary_text = "\n".join(summary_lines)
        finding = TemporalFinding(
            summary=summary_text,
            clusters=clusters,
            timeline=timeline,
            claims=v_claims,
            diff_status=diff_status,
            has_prior_baseline=has_prior_baseline
        )

        elapsed = (time.time() - start_time) * 1000
        return TemporalResponse(
            query=request.query,
            intent=intent,
            status="COMPLETE",
            window=window,
            clusters=clusters,
            timeline=timeline,
            finding=finding,
            grounding_status=r_resp.grounding_status,
            latency_ms=elapsed
        )


web_temporal_service = WebTemporalService()
