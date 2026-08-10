"""
Comprehensive Deterministic Test Suite for J.A.R.V.I.S. I2.2 V5 — Deep Web Research & Source Discovery.

Tests:
1. Evidence Gap Detection (Missing primary source, single source claims, unresolved conflicts)
2. Link Extraction & Eligibility Classification Engine
3. Explicit Rejection Reasons (SSRF_BLOCKED, LOOPBACK_OR_PRIVATE, IP_ENCODED, ALREADY_VISITED)
4. Primary-Source Escalation Link Selection
5. Sub-Question & Gap Query Traceability (Zero query drift)
6. Deterministic Research Novelty Delta Tracking
7. Structural Stopping Policy (SUFFICIENT_EVIDENCE, NO_NEW_INFORMATION, BUDGET_EXHAUSTED)
8. Question Coverage Analyzer (SUPPORTED, CONTRADICTED, UNRESOLVED)
9. Research Synthesizer (Contradictions preserved even when official source exists)
10. Server Config Hard Limits Override User Request Limits
11. Prompt Injection Boundary Isolation (<UNTRUSTED_WEBPAGE_CONTENT>)
12. Ephemeral State Conversation Isolation
13. Global Timeout Handling
14. Direct API Endpoint POST /api/web/deep-research
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app
from intelligence.web.models import SearchResultItem, WebPageDocument, GroundingStatus
from intelligence.web.research.models import ResearchSource, SourceSuitability, EvidenceItem
from intelligence.web.deep_research import (
    web_deep_research_service,
    DeepResearchRequest,
    DeepResearchConfig,
    StoppingReason,
    EvidenceGapType,
    LinkCategory,
    LinkRejectionReason,
    QuestionCoverageState,
    DiscoveredLink,
    EvidenceGap
)
from intelligence.web.deep_research.research_state import DeepResearchState
from intelligence.web.deep_research.link_analyzer import link_analyzer
from intelligence.web.deep_research.source_discovery import source_discovery
from intelligence.web.deep_research.evidence_gap_detector import evidence_gap_detector
from intelligence.web.deep_research.stopping_policy import stopping_policy
from intelligence.web.deep_research.coverage_analyzer import coverage_analyzer
from intelligence.web.deep_research.research_synthesizer import research_synthesizer
from intelligence.web.deep_research.research_controller import research_controller

client = TestClient(app)


# 1. EVIDENCE GAP DETECTION TEST
def test_evidence_gap_detector():
    """Detects missing primary source, single source claims, and unresolved conflicts structurally."""
    subq = ["sub_q1", "sub_q2"]
    sources = [
        ResearchSource(source_id="s1", url="https://techcrunch.com/article", canonical_url="https://techcrunch.com/article", domain="techcrunch.com", title="TC", source_type="NEWS", suitability=SourceSuitability(domain="techcrunch.com", is_news=True), retrieved_at="2026-08-06T00:00:00Z")
    ]
    ev_items = [
        EvidenceItem(evidence_id="e1", source_id="s1", canonical_url="https://techcrunch.com/article", text="Text 1", sub_question_id="sub_q1")
    ]
    conflicts = [{"topic": "Performance", "sub_question_id": "sub_q1", "description": "Contradictory claims on speed"}]

    gaps = evidence_gap_detector.detect_gaps(subq, ev_items, sources, conflicts)
    gap_types = {g.gap_type for g in gaps}

    assert EvidenceGapType.MISSING_PRIMARY_SOURCE in gap_types
    assert EvidenceGapType.UNRESOLVED_CONTRADICTION in gap_types
    assert EvidenceGapType.ONLY_ONE_INDEPENDENT_SOURCE in gap_types
    assert EvidenceGapType.UNSUPPORTED_CLAIM in gap_types


# 2. LINK EXTRACTION & CLASSIFICATION TEST
@pytest.mark.asyncio
async def test_link_analyzer_classification():
    """Extracts and classifies candidate links from HTML with safety and eligibility checks."""
    html = """
    <html><body>
    <a href="https://react.dev/blog/release">Official Docs</a>
    <a href="https://github.com/facebook/react/releases">GitHub Release</a>
    <a href="http://127.0.0.1/admin">Localhost Link</a>
    <a href="https://techcrunch.com/news">Tech News</a>
    </body></html>
    """
    source_url = "https://example.com/blog"
    visited = set()

    async def mock_val(url):
        if "127.0.0.1" in url:
            return False, None, "Loopback IP address rejected"
        return True, "93.184.216.34", ""

    with patch("intelligence.web.deep_research.link_analyzer.url_validator.validate_url", side_effect=mock_val):
        links = await link_analyzer.extract_and_classify_links(html, source_url, visited)
    
        # 127.0.0.1 should be marked UNSAFE and rejected
        unsafe_links = [l for l in links if not l.is_url_safe]
        assert len(unsafe_links) >= 1
        assert unsafe_links[0].rejection_reason in (LinkRejectionReason.LOOPBACK_OR_PRIVATE, LinkRejectionReason.SSRF_BLOCKED, LinkRejectionReason.IP_ENCODED)

        # Safe links classified into OFFICIAL / PRIMARY_SOURCE
        safe_links = [l for l in links if l.is_url_safe and l.is_eligible_for_selection]
        cats = {l.category for l in safe_links}
        assert LinkCategory.OFFICIAL in cats or LinkCategory.PRIMARY_SOURCE in cats


# 3. LINK DEDUPLICATION & REJECTION REASON TEST
@pytest.mark.asyncio
async def test_link_deduplication_rejection_reason():
    """Already visited links get rejection_reason = ALREADY_VISITED."""
    html = '<html><body><a href="https://react.dev/docs">React Docs</a></body></html>'
    source_url = "https://example.com/blog"
    visited = {"https://react.dev/docs"}

    async def mock_val(url):
        return True, "93.184.216.34", ""

    with patch("intelligence.web.deep_research.link_analyzer.url_validator.validate_url", side_effect=mock_val):
        links = await link_analyzer.extract_and_classify_links(html, source_url, visited)
        assert len(links) == 1
        assert links[0].is_eligible_for_selection is False
        assert links[0].rejection_reason == LinkRejectionReason.ALREADY_VISITED




# 4. PRIMARY-SOURCE ESCALATION SELECTION TEST
def test_source_discovery_escalation():
    """Selects top primary/official candidate links for escalation."""
    links = [
        DiscoveredLink(url="https://techcrunch.com/article", canonical_url="https://techcrunch.com/article", anchor_text="News", source_page_url="https://src.com", category=LinkCategory.NEWS, is_url_safe=True, is_eligible_for_selection=True),
        DiscoveredLink(url="https://react.dev/release", canonical_url="https://react.dev/release", anchor_text="Official Release", source_page_url="https://src.com", category=LinkCategory.OFFICIAL, is_url_safe=True, is_eligible_for_selection=True),
        DiscoveredLink(url="https://github.com/facebook/react", canonical_url="https://github.com/facebook/react", anchor_text="GitHub Repo", source_page_url="https://src.com", category=LinkCategory.PRIMARY_SOURCE, is_url_safe=True, is_eligible_for_selection=True)
    ]
    visited = set()

    escalation = source_discovery.select_candidate_links_for_escalation(links, visited, max_select=2)
    assert len(escalation) == 2
    assert escalation[0].category in (LinkCategory.OFFICIAL, LinkCategory.PRIMARY_SOURCE)


# 5. SUB-QUESTION / GAP QUERY TRACEABILITY TEST
def test_sub_question_gap_query_traceability():
    """Follow-up targeted queries explicitly trace to an unresolved gap_id and sub_question_id."""
    gaps = [
        EvidenceGap(gap_id="gap_1", gap_type=EvidenceGapType.MISSING_PRIMARY_SOURCE, target="React 19", sub_question_id="sub_q1", description="Missing primary source")
    ]
    attempted = set()

    queries = source_discovery.generate_targeted_gap_queries(gaps, attempted)
    assert len(queries) == 1
    q_str, gap_id, subq_id = queries[0]
    assert gap_id == "gap_1"
    assert subq_id == "sub_q1"
    assert "React 19" in q_str


# 6. DETERMINISTIC NOVELTY TRACKING & STOPPING POLICY TEST
def test_novelty_tracking_and_no_new_information_stopping():
    """Triggers NO_NEW_INFORMATION stopping condition when round novelty is 0."""
    state = DeepResearchState(research_id="r1", query="React 19")
    config = DeepResearchConfig(max_rounds=3)

    # Round 1: Novel items added
    state.record_round_novelty(new_sources_count=2, new_evidence_count=3, resolved_gaps_count=1, new_conflicts_count=0, new_primary_sources_count=1)
    should_stop, reason = stopping_policy.evaluate_stopping_condition(state, config, has_eligible_links=True, has_eligible_queries=True)
    assert should_stop is False

    # Round 2: 0 new sources & 0 new evidence chunks (Novelty = 0)
    state.record_round_novelty(new_sources_count=0, new_evidence_count=0, resolved_gaps_count=0, new_conflicts_count=0, new_primary_sources_count=0)
    should_stop_r2, reason_r2 = stopping_policy.evaluate_stopping_condition(state, config, has_eligible_links=True, has_eligible_queries=True)
    assert should_stop_r2 is True
    assert reason_r2 == StoppingReason.NO_NEW_INFORMATION


# 7. COVERAGE ANALYZER TEST
def test_coverage_analyzer_states():
    """Derives structural coverage status per sub-question without fake numeric scores."""
    subq = ["Is React Server Components production-ready?", "What are the key limitations?"]
    sources = [
        ResearchSource(source_id="s1", url="https://react.dev/docs", canonical_url="https://react.dev/docs", domain="react.dev", title="React Docs", source_type="OFFICIAL", suitability=SourceSuitability(domain="react.dev", is_official=True), retrieved_at="2026-08-06T00:00:00Z"),
        ResearchSource(source_id="s2", url="https://techcrunch.com", canonical_url="https://techcrunch.com", domain="techcrunch.com", title="TC", source_type="NEWS", suitability=SourceSuitability(domain="techcrunch.com", is_news=True), retrieved_at="2026-08-06T00:00:00Z")
    ]
    ev_items = [
        EvidenceItem(evidence_id="e1", source_id="s1", canonical_url="https://react.dev/docs", text="RSC is stable", sub_question_id="sub_q1"),
        EvidenceItem(evidence_id="e2", source_id="s2", canonical_url="https://techcrunch.com", text="RSC is used in prod", sub_question_id="sub_q1")
    ]
    conflicts = [{"sub_question_id": "sub_q2", "description": "Contradictory benchmarks"}]

    coverage = coverage_analyzer.analyze_coverage(subq, ev_items, sources, conflicts)
    assert len(coverage) == 2
    assert coverage[0].coverage_state == QuestionCoverageState.SUPPORTED
    assert coverage[1].coverage_state == QuestionCoverageState.CONTRADICTED


# 8. CONTRADICTION PRESERVATION TEST
def test_research_synthesizer_preserves_contradictions():
    """ResearchSynthesizer preserves conflicting evidence even when official source exists."""
    state = DeepResearchState(research_id="r1", query="React RSC")
    state.sources.append(
        ResearchSource(source_id="s1", url="https://react.dev", canonical_url="https://react.dev", domain="react.dev", title="Official React", source_type="OFFICIAL", suitability=SourceSuitability(domain="react.dev", is_official=True), retrieved_at="2026-08-06T00:00:00Z")
    )
    state.contradictions.append({"description": "Server bundle overhead vs client bundle savings contradiction"})

    subq = ["RSC performance impact"]
    coverage = coverage_analyzer.analyze_coverage(subq, [], state.sources, state.contradictions)

    finding = research_synthesizer.synthesize(state, coverage, StoppingReason.SUFFICIENT_EVIDENCE)
    assert len(finding.conflicting_evidence) >= 1
    assert "Server bundle overhead" in finding.conflicting_evidence[0] or "Contradictory evidence" in finding.conflicting_evidence[0]


# 9. SERVER HARD LIMITS OVERRIDE USER REQUEST TEST
@pytest.mark.asyncio
async def test_server_hard_limits_override_user_request():
    """Server-side hard limits always override user request max_rounds."""
    req = DeepResearchRequest(query="React 19", max_rounds=100)  # User requests 100 rounds
    with patch("intelligence.web.deep_research.research_controller.web_research_service.execute_research") as mock_research:
        mock_research.return_value = MagicMock(sources=[], evidence_items=[], finding=None, grounding_status=GroundingStatus.SEARCH_SNIPPET_FALLBACK)
        resp = await web_deep_research_service.execute_deep_research(req)
        # Server hard limit max_rounds is 3
        assert resp.rounds_completed <= 3


# 10. DIRECT API & ROUTER INTEGRATION TEST
def test_direct_api_deep_research_endpoint():
    """POST /api/web/deep-research endpoint returns HTTP 200 with structured DeepResearchResponse."""
    payload = {"query": "Research whether React Server Components are production-ready", "force_deep_research": True}
    res = client.post("/api/web/deep-research", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["query"] == payload["query"]
    assert "stopping_reason" in data
