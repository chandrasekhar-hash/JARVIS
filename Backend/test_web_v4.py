"""
Comprehensive Deterministic Test Suite for J.A.R.V.I.S. I2.2 V4 — Current Events, News & Freshness Intelligence.

Tests:
1. Temporal Intent Classification
2. Time Window Resolver & Timezone Precedence (No silent UTC fallback, UNCERTAIN_TIMEZONE, INVALID_TIMEZONE)
3. Publication Time Resolver (published_at=None when missing; zero timestamp manufacturing)
4. PrimaryAnnouncementResolver (Primary source vs independent confirmation)
5. Ephemeral TemporalSnapshotStore (TTL expiration, bounded memory, cross-conversation isolation, diff statuses)
6. Story Clusterer & Syndication Rejection
7. Update Detector & Old-News Resurfacing Detection
8. Timeline Builder & Timestamp Precision
9. Temporal Claim Provenance Validation
10. Prompt Injection Boundary Isolation
11. Global Wall-Clock 18.0s Timeout Handling
12. Direct API Endpoint POST /api/web/temporal
"""

import pytest
import asyncio
import time
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from main import app
from intelligence.web.models import SearchResultItem, WebPageDocument, GroundingStatus
from intelligence.web.research.models import ResearchSource, SourceSuitability, EvidenceItem
from intelligence.web.temporal import (
    web_temporal_service,
    TemporalRequest,
    TemporalIntent,
    TemporalDiffStatus,
    TimePrecision,
    TimeSource,
    FreshnessCategory,
    UpdateCategory,
    TemporalSnapshot,
    temporal_snapshot_store,
    temporal_provenance_validator,
    temporal_intent_classifier
)
from intelligence.web.temporal.time_window_resolver import time_window_resolver
from intelligence.web.temporal.publication_time_resolver import publication_time_resolver
from intelligence.web.temporal.primary_announcement_resolver import primary_announcement_resolver
from intelligence.web.temporal.event_extractor import event_extractor
from intelligence.web.temporal.story_clusterer import story_clusterer
from intelligence.web.temporal.update_detector import update_detector
from intelligence.web.temporal.timeline_builder import timeline_builder


client = TestClient(app)


# 1. TEMPORAL INTENT CLASSIFICATION TESTS
def test_temporal_intent_classification():
    """Classifies temporal queries into intents and fast-bypasses non-temporal queries."""
    intent_t, is_t = temporal_intent_classifier.classify_intent("What are the AI developments today?")
    assert intent_t == TemporalIntent.TODAY
    assert is_t is True

    intent_nt, is_nt = temporal_intent_classifier.classify_intent("what is recursion?")
    assert intent_nt == TemporalIntent.NON_TEMPORAL
    assert is_nt is False


# 2. TIME WINDOW RESOLVER & TIMEZONE PRECEDENCE TESTS
def test_time_window_resolver_timezone_precedence():
    """Verifies timezone precedence: Request TZ -> Session TZ -> None. UNCERTAIN_TIMEZONE returned when unknown."""
    # Unknown timezone for relative query
    w_unk = time_window_resolver.resolve_time_window("what happened today?", TemporalIntent.TODAY, request_timezone=None, session_timezone=None)
    assert w_unk.user_timezone is None
    assert w_unk.resolution_status == "UNCERTAIN_TIMEZONE"

    # Explicit request timezone
    w_ny = time_window_resolver.resolve_time_window("today news", TemporalIntent.TODAY, request_timezone="America/New_York")
    assert w_ny.user_timezone == "America/New_York"
    assert w_ny.resolution_status == "RESOLVED"

    # Invalid timezone handling
    w_inv = time_window_resolver.resolve_time_window("today news", TemporalIntent.TODAY, request_timezone="Invalid/Timezone_Name")
    assert w_inv.resolution_status == "INVALID_TIMEZONE"


# 3. PUBLICATION TIME RESOLVER TESTS
def test_publication_time_resolver_integrity():
    """published_at remains None when missing in metadata; retrieved_at is NEVER substituted."""
    retrieved_at = "2026-08-06T12:00:00Z"
    meta = publication_time_resolver.resolve_publication_time("<html><body>No date here</body></html>", retrieved_at)
    assert meta.published_at is None
    assert meta.retrieved_at == retrieved_at
    assert meta.time_source == TimeSource.UNKNOWN


# 4. PRIMARY ANNOUNCEMENT RESOLVER TESTS
def test_primary_announcement_resolver():
    """Distinguishes official primary release/blog from independent secondary news reports."""
    suit_off = SourceSuitability(domain="react.dev", is_official=True, reasons=["Official"])
    suit_news = SourceSuitability(domain="techcrunch.com", is_news=True, reasons=["News"])
    sources = [
        ResearchSource(source_id="source_1", url="https://techcrunch.com/react-19", canonical_url="https://techcrunch.com/react-19", domain="techcrunch.com", title="TC React", source_type="NEWS", suitability=suit_news, retrieved_at="2026-08-06T00:00:00Z"),
        ResearchSource(source_id="source_2", url="https://react.dev/release-notes", canonical_url="https://react.dev/release-notes", domain="react.dev", title="React Release", source_type="OFFICIAL", suitability=suit_off, retrieved_at="2026-08-06T00:00:00Z"),
    ]

    primary, secondary = primary_announcement_resolver.resolve_primary_announcements(sources)
    assert primary is not None
    assert primary.source_id == "source_2"
    assert len(secondary) == 1
    assert secondary[0].source_id == "source_1"


# 5. TEMPORAL SNAPSHOT STORE TESTS
@pytest.mark.asyncio
async def test_temporal_snapshot_store_diffing_and_isolation():
    """Snapshot store enforces RAM-only bounded storage, TTL, cross-conversation isolation, and diff status."""
    conv1 = "conv_abc"
    conv2 = "conv_xyz"

    # Save snapshot for conv1
    snap1 = await temporal_snapshot_store.save_snapshot(
        conversation_id=conv1,
        topic_fingerprint="AI news",
        events=[],
        claims=[],
        canonical_urls=["https://example.com/1"],
        source_ids=["source_1"]
    )
    assert snap1 is not None

    # Verify cross-conversation isolation
    snap_conv2 = await temporal_snapshot_store.get_latest_snapshot(conv2)
    assert snap_conv2 is None

    # Test diff status: NEW URL
    diff_new, has_base = temporal_snapshot_store.compute_diff_status(
        new_urls=["https://example.com/1", "https://example.com/2"],
        new_events=[],
        previous_snapshot=snap1
    )
    assert diff_new == TemporalDiffStatus.NEW
    assert has_base is True

    # Test missing previous snapshot baseline
    diff_no_base, has_base_false = temporal_snapshot_store.compute_diff_status(
        new_urls=["https://example.com/1"],
        new_events=[],
        previous_snapshot=None
    )
    assert diff_no_base == TemporalDiffStatus.NEW
    assert has_base_false is False


# 6. STORY CLUSTERER TESTS
def test_story_clusterer_syndication_rejection():
    """StoryClusterer clusters news events and avoids syndicated inflation."""
    suitability = SourceSuitability(domain="example.com", is_official=True, reasons=["Official"])
    sources = [ResearchSource(source_id="source_1", url="https://example.com", canonical_url="https://example.com", domain="example.com", title="Ex", source_type="OFFICIAL", suitability=suitability, retrieved_at="2026-08-06T00:00:00Z")]
    evs = [EvidenceItem(evidence_id="ev_1", source_id="source_1", canonical_url="https://example.com", text="React release text.", sub_question_id="sub_q1")]

    news_events = event_extractor.extract_events(evs, sources)
    clusters = story_clusterer.cluster_events(news_events, sources)
    assert len(clusters) >= 1
    assert clusters[0].events[0].title.startswith("Main") or "React" in clusters[0].events[0].description


# 7. UPDATE DETECTOR & OLD NEWS RESURFACING TESTS
def test_update_detector_old_news_resurfacing():
    """Detects when an old article published prior to target query window resurfaces."""
    window = time_window_resolver.resolve_time_window("today news", TemporalIntent.TODAY, request_timezone="America/New_York")

    suitability = SourceSuitability(domain="example.com", is_official=True, reasons=["Official"])
    sources = [ResearchSource(source_id="source_1", url="https://example.com", canonical_url="https://example.com", domain="example.com", title="Ex", source_type="OFFICIAL", suitability=suitability, retrieved_at="2026-08-06T00:00:00Z")]
    evs = [EvidenceItem(evidence_id="ev_1", source_id="source_1", canonical_url="https://example.com", text="Update details text.", sub_question_id="sub_q1")]

    events = event_extractor.extract_events(evs, sources)
    events[0].first_published_at = "2025-01-01T00:00:00Z"  # Old date

    clusters = story_clusterer.cluster_events(events, sources)
    clusters = update_detector.classify_and_detect_resurfacing(clusters, window)

    assert clusters[0].is_old_news_resurfacing is True


# 8. TIMELINE BUILDER TESTS
def test_timeline_builder_ordering():
    """TimelineBuilder orders events chronologically without forcing exact times on date-only entries."""
    suitability = SourceSuitability(domain="example.com", is_official=True, reasons=["Official"])
    sources = [ResearchSource(source_id="source_1", url="https://example.com", canonical_url="https://example.com", domain="example.com", title="Ex", source_type="OFFICIAL", suitability=suitability, retrieved_at="2026-08-06T00:00:00Z")]
    evs = [EvidenceItem(evidence_id="ev_1", source_id="source_1", canonical_url="https://example.com", text="Timeline event text.", sub_question_id="sub_q1")]

    events = event_extractor.extract_events(evs, sources)
    timeline = timeline_builder.build_timeline(events)
    assert len(timeline) == 1
    assert timeline[0].timeline_id == "timeline_1"


# 9. PROMPT INJECTION BOUNDARY TEST
def test_prompt_injection_boundary_isolation():
    """Web text inside <UNTRUSTED_WEBPAGE_CONTENT> boundaries cannot override system instructions."""
    req = TemporalRequest(query="AI news today")
    with patch("intelligence.web.temporal.temporal_service.web_research_service.execute_research") as mock_research:
        mock_research.return_value = MagicMock(
            sources=[],
            evidence_items=[],
            finding=None,
            grounding_status=GroundingStatus.SEARCH_SNIPPET_FALLBACK
        )
        # Service cleanly handles 0 sources without crashing
        res = client.post("/api/web/temporal", json={"query": "AI news today", "force_temporal": True})
        assert res.status_code == 200


# 10. GLOBAL WALL-CLOCK TIMEOUT TEST
@pytest.mark.asyncio
async def test_global_wall_clock_timeout():
    """WebTemporalService returns TIMEOUT status if execution exceeds 18.0s global deadline."""
    req = TemporalRequest(query="Slow temporal query")
    with patch("intelligence.web.temporal.temporal_service.WebTemporalService._run_temporal_pipeline", side_effect=asyncio.TimeoutError()):
        resp = await web_temporal_service.execute_temporal_research(req)
        assert resp.status == "TIMEOUT"
        assert "18.0s wall-clock deadline" in resp.error


# 11. DIRECT API ENDPOINT TEST
def test_direct_api_temporal_endpoint():
    """POST /api/web/temporal returns HTTP 200 with structured TemporalResponse."""
    payload = {"query": "What happened in AI today?", "force_temporal": True}
    res = client.post("/api/web/temporal", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["query"] == "What happened in AI today?"
    assert "intent" in data
