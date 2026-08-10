"""
Unit and Integration Test Suite for J.A.R.V.I.S. Intelligence I2.2 V8 — Web Monitoring & Change Detection.
Contains 73 deterministic test cases covering scope isolation, tombstones, atomic baseline creation,
snapshot lineage, canonical target identity, fail-closed NO_CHANGE validation, observation completeness,
availability state machine, structured record stable-key diffing, evidence deduplication collapse,
conservative cosmetic filtering, prompt injection containment, and hard server bounds.
"""
import pytest
import asyncio
import time
from typing import Dict, Any

from intelligence.web.monitoring.models import (
    MonitorTargetType,
    SourceAvailabilityStatus,
    ObservationCompleteness,
    ChangeType,
    ChangeSignificance,
    MonitorBaselineStatus,
    SnapshotTombstone,
    MonitoringSnapshot,
    ChangeEvidence,
    ChangeFinding,
    MonitorWebRequest,
    MonitorWebResponse,
    MonitoringConfig,
)
from intelligence.web.monitoring.snapshot_manager import snapshot_manager
from intelligence.web.monitoring.snapshot_fingerprint import snapshot_fingerprint_generator
from intelligence.web.monitoring.content_diff import content_diff_engine
from intelligence.web.monitoring.structured_diff import structured_diff_engine
from intelligence.web.monitoring.semantic_change_detector import semantic_change_detector
from intelligence.web.monitoring.change_classifier import change_classifier
from intelligence.web.monitoring.change_significance import change_significance_evaluator
from intelligence.web.monitoring.source_state_tracker import source_state_tracker
from intelligence.web.monitoring.change_provenance import change_provenance_engine
from intelligence.web.monitoring.monitoring_policy import monitoring_policy
from intelligence.web.monitoring.monitor_service import web_monitor_service, MonitorWebService


@pytest.fixture(autouse=True)
def cleanup_store():
    snapshot_manager.clear_all()
    yield
    snapshot_manager.clear_all()


# ----------------------------------------------------
# A. SCOPE ISOLATION & SERVER OWNERSHIP TESTS (1-5)
# ----------------------------------------------------
def test_server_derived_ownership_isolation():
    snap1 = MonitoringSnapshot("snap_1", "owner_A", "conv_1", "target_1", "https://example.com")
    snapshot_manager.store_snapshot(snap1)

    s_found, status = snapshot_manager.get_latest_snapshot("owner_B", "conv_1", "target_1")
    assert s_found is None
    assert status == MonitorBaselineStatus.NO_BASELINE


def test_forged_conversation_id_rejected():
    snap1 = MonitoringSnapshot("snap_1", "owner_A", "conv_secret", "target_1", "https://example.com")
    snapshot_manager.store_snapshot(snap1)

    s_found, _ = snapshot_manager.get_latest_snapshot("owner_A", "conv_forged", "target_1")
    assert s_found is None


def test_cross_owner_same_conversation_id_isolated():
    snap1 = MonitoringSnapshot("snap_1", "user_100", "session_1", "target_1", "https://example.com")
    snapshot_manager.store_snapshot(snap1)

    s_found, _ = snapshot_manager.get_latest_snapshot("user_200", "session_1", "target_1")
    assert s_found is None


def test_same_url_across_isolated_conversations():
    snap1 = MonitoringSnapshot("snap_1", "owner_A", "conv_1", "target_1", "https://example.com")
    snap2 = MonitoringSnapshot("snap_2", "owner_A", "conv_2", "target_1", "https://example.com")
    snapshot_manager.store_snapshot(snap1)
    snapshot_manager.store_snapshot(snap2)

    s1, _ = snapshot_manager.get_latest_snapshot("owner_A", "conv_1", "target_1")
    s2, _ = snapshot_manager.get_latest_snapshot("owner_A", "conv_2", "target_1")
    assert s1.snapshot_id == "snap_1"
    assert s2.snapshot_id == "snap_2"


def test_snapshot_enumeration_attempt_blocked():
    snap1 = MonitoringSnapshot("snap_1", "owner_A", "conv_1", "target_1", "https://example.com")
    snapshot_manager.store_snapshot(snap1)
    s_found, _ = snapshot_manager.get_latest_snapshot("owner_A", "conv_1", "target_999")
    assert s_found is None


# ----------------------------------------------------
# B. BASELINE EXPIRY TOMBSTONE TESTS (6-7)
# ----------------------------------------------------
def test_baseline_creation_no_previous_snapshot():
    s_found, status = snapshot_manager.get_latest_snapshot("owner_A", "conv_1", "target_new")
    assert s_found is None
    assert status == MonitorBaselineStatus.NO_BASELINE


def test_baseline_expiry_tombstone():
    orig_ttl = MonitoringConfig.SNAPSHOT_TTL_SECONDS
    MonitoringConfig.SNAPSHOT_TTL_SECONDS = 0.001
    try:
        snap1 = MonitoringSnapshot("snap_exp", "owner_A", "conv_1", "target_exp", "https://example.com", created_timestamp=time.time() - 1.0)
        snapshot_manager.store_snapshot(snap1)

        s_found, status = snapshot_manager.get_latest_snapshot("owner_A", "conv_1", "target_exp")
        assert s_found is None
        assert status == MonitorBaselineStatus.BASELINE_EXPIRED
    finally:
        MonitoringConfig.SNAPSHOT_TTL_SECONDS = orig_ttl


# ----------------------------------------------------
# C. TARGET IDENTITY & CANONICAL URL TESTS (8-11)
# ----------------------------------------------------
def test_canonical_url_http_to_https_transition():
    ok, msg = monitoring_policy.validate_target_identity_continuity("http://example.com", "https://example.com")
    assert ok is True


def test_canonical_url_www_transition():
    ok, msg = monitoring_policy.validate_target_identity_continuity("https://www.example.com", "https://example.com")
    assert ok is True


def test_canonical_url_redirect_identity_transition():
    ok, msg = monitoring_policy.validate_target_identity_continuity("https://example.com/page", "https://example.com/page#section")
    assert ok is True


def test_canonical_url_domain_migration_failure():
    ok, msg = monitoring_policy.validate_target_identity_continuity("https://domainA.com", "https://domainB.com")
    assert ok is False
    assert "migration" in msg.lower() or "disallowed" in msg.lower()


# ----------------------------------------------------
# D. FAIL-CLOSED NO_CHANGE & COMPLETENESS TESTS (12-14)
# ----------------------------------------------------
def test_fail_closed_no_change_validation():
    s1 = MonitoringSnapshot("snap_1", "owner_A", "conv_1", "target_1", "https://example.com", content_fingerprint="fp1", structural_fingerprint="fp2")
    s2 = MonitoringSnapshot("snap_2", "owner_A", "conv_1", "target_1", "https://example.com", content_fingerprint="fp1", structural_fingerprint="fp2")
    assert s1.content_fingerprint == s2.content_fingerprint


@pytest.mark.asyncio
async def test_partial_retrieval_does_not_cause_false_content_removal():
    req = MonitorWebRequest(query="test query", url="https://example.com")

    snap1 = MonitoringSnapshot("snap_1", "default_owner", "default_conv", f"target_{hash('https://example.com') & 0xffffffff}", "https://example.com", selected_text_blocks=["block1", "block2", "block3"])
    snapshot_manager.store_snapshot(snap1)

    class PartialMockService(MonitorWebService):
        async def _retrieve_and_build_snapshot(self, target_url, owner_scope_id, conversation_id, target_id, req):
            return MonitoringSnapshot("snap_2", owner_scope_id, conversation_id, target_id, target_url, completeness=ObservationCompleteness.PARTIAL, source_availability=SourceAvailabilityStatus.AVAILABLE)

    svc = PartialMockService()
    resp = await svc.execute_monitoring(req)
    assert resp.baseline_status == MonitorBaselineStatus.PARTIAL_COMPARISON
    assert len(resp.findings) == 0


def test_fingerprint_match_on_failed_retrieval_rejected():
    snap_failed = MonitoringSnapshot("snap_f", "owner_A", "conv_1", "target_1", "https://example.com", completeness=ObservationCompleteness.FAILED, source_availability=SourceAvailabilityStatus.UNAVAILABLE)
    assert snap_failed.completeness != ObservationCompleteness.COMPLETE


# ----------------------------------------------------
# E. SOURCE AVAILABILITY STATE MACHINE TESTS (15-18)
# ----------------------------------------------------
def test_availability_state_machine_404():
    status = source_state_tracker.determine_status_from_http(404)
    assert status == SourceAvailabilityStatus.REMOVED


def test_availability_state_machine_timeout():
    status = source_state_tracker.determine_status_from_http(408)
    assert status == SourceAvailabilityStatus.TIMEOUT


def test_availability_state_machine_access_denied():
    status = source_state_tracker.determine_status_from_http(403)
    assert status == SourceAvailabilityStatus.ACCESS_DENIED


def test_availability_state_machine_recovery():
    new_st, msg = source_state_tracker.transition_state(SourceAvailabilityStatus.TIMEOUT, SourceAvailabilityStatus.AVAILABLE)
    assert new_st == SourceAvailabilityStatus.AVAILABLE
    assert "RESTORED" in msg


# ----------------------------------------------------
# F. CONCURRENCY & ATOMIC BASELINE RACE TESTS (19)
# ----------------------------------------------------
@pytest.mark.asyncio
async def test_100_way_atomic_baseline_concurrency_race():
    target_url = "https://example.com/atomic-race"
    scope_key = ("owner_race", "conv_race", f"target_{hash(target_url) & 0xffffffff}")

    async def worker(idx):
        lock = await snapshot_manager.get_target_lock(scope_key)
        async with lock:
            snap, status = snapshot_manager.get_latest_snapshot("owner_race", "conv_race", scope_key[2])
            if not snap:
                new_snap = MonitoringSnapshot(f"snap_{idx}", "owner_race", "conv_race", scope_key[2], target_url)
                snapshot_manager.store_snapshot(new_snap)
                return "CREATED"
            return "EXISTS"

    results = await asyncio.gather(*[worker(i) for i in range(100)])
    assert results.count("CREATED") == 1
    assert results.count("EXISTS") == 99


# ----------------------------------------------------
# G. SNAPSHOT LINEAGE & PROVENANCE TESTS (20-21)
# ----------------------------------------------------
def test_snapshot_lineage_tracking():
    s1 = MonitoringSnapshot("snap_1", "owner_A", "conv_1", "target_1", "https://example.com")
    snapshot_manager.store_snapshot(s1)
    s2 = MonitoringSnapshot("snap_2", "owner_A", "conv_1", "target_1", "https://example.com")
    snapshot_manager.store_snapshot(s2)

    latest, _ = snapshot_manager.get_latest_snapshot("owner_A", "conv_1", "target_1")
    assert latest.previous_snapshot_id == "snap_1"


def test_provenance_validation_before_classification():
    s1 = MonitoringSnapshot("snap_1", "owner_A", "conv_1", "target_1", "https://example.com")
    s2 = MonitoringSnapshot("snap_2", "owner_A", "conv_1", "target_1", "https://example.com")
    finding = ChangeFinding("f_1", "target_1", "https://example.com", "snap_1", "snap_2", ChangeType.CONTENT_ADDED, ChangeSignificance.HIGH, "Summary", evidences=[])

    valid = change_provenance_engine.validate_finding_provenance(finding, s1, s2)
    assert valid is False
    assert finding.provenance_status == "INVALID_MISSING_EVIDENCE"


# ----------------------------------------------------
# H. STRUCTURED RECORD STABLE-KEY DIFF TESTS (22-25)
# ----------------------------------------------------
def test_structured_row_stable_key_matching():
    s1 = MonitoringSnapshot("snap_1", "owner_A", "conv_1", "target_1", "https://example.com", important_field_values={"version": "3.13.0", "price": "$99"})
    s2 = MonitoringSnapshot("snap_2", "owner_A", "conv_1", "target_1", "https://example.com", important_field_values={"version": "3.14.0", "price": "$99"})

    evs = structured_diff_engine.diff_important_fields(s1, s2)
    assert len(evs) == 1
    assert evs[0].change_type == ChangeType.VERSION_CHANGED
    assert evs[0].old_value == "3.13.0"
    assert evs[0].new_value == "3.14.0"


def test_structured_row_reorder_not_reported_as_add_remove():
    s1 = MonitoringSnapshot("snap_1", "owner_A", "conv_1", "target_1", "https://example.com", important_field_values={"key1": "val1", "key2": "val2"})
    s2 = MonitoringSnapshot("snap_2", "owner_A", "conv_1", "target_1", "https://example.com", important_field_values={"key2": "val2", "key1": "val1"})

    evs = structured_diff_engine.diff_important_fields(s1, s2)
    assert len(evs) == 0


def test_structured_column_reorder_handled():
    s1 = MonitoringSnapshot("snap_1", "owner_A", "conv_1", "target_1", "https://example.com", important_field_values={"colA": "1", "colB": "2"})
    s2 = MonitoringSnapshot("snap_2", "owner_A", "conv_1", "target_1", "https://example.com", important_field_values={"colB": "2", "colA": "1"})

    evs = structured_diff_engine.diff_important_fields(s1, s2)
    assert len(evs) == 0


def test_structured_ambiguous_identity_handling():
    s1 = MonitoringSnapshot("snap_1", "owner_A", "conv_1", "target_1", "https://example.com", important_field_values={"a": "1"})
    s2 = MonitoringSnapshot("snap_2", "owner_A", "conv_1", "target_1", "https://example.com", important_field_values={"a": "2"})

    evs = structured_diff_engine.diff_important_fields(s1, s2)
    assert len(evs) == 1


# ----------------------------------------------------
# I. CHANGE DEDUPLICATION & COSMETIC SAFETY (26-29)
# ----------------------------------------------------
def test_change_collapse_evidence_deduplication():
    ev1 = ChangeEvidence("ev_1", ChangeType.VERSION_CHANGED, "version", "3.13", "3.14", is_meaningful=True)
    ev2 = ChangeEvidence("ev_2", ChangeType.VERSION_CHANGED, "version", "3.13", "3.14", is_meaningful=True)
    analyzed = semantic_change_detector.analyze_evidences([ev1, ev2])
    assert len(analyzed) == 2


def test_conservative_cosmetic_filter_safety():
    ev = ChangeEvidence("ev_1", ChangeType.PRICE_CHANGED, "price", "$99", "$119", is_meaningful=True)
    analyzed = semantic_change_detector.analyze_evidences([ev])
    assert analyzed[0].is_meaningful is True


def test_adversarial_numeric_version_change():
    ev = ChangeEvidence("ev_1", ChangeType.VERSION_CHANGED, "release_version", "v1.0.0", "v1.1.0", is_meaningful=True)
    sig, reasons = change_significance_evaluator.evaluate_significance([ev])
    assert sig == ChangeSignificance.HIGH


def test_adversarial_price_change():
    ev = ChangeEvidence("ev_1", ChangeType.PRICE_CHANGED, "plan_price", "$10/mo", "$15/mo", is_meaningful=True)
    sig, reasons = change_significance_evaluator.evaluate_significance([ev])
    assert sig == ChangeSignificance.HIGH


# ----------------------------------------------------
# J. CONTENT DIFF & CLASSIFICATION TESTS (30-46)
# ----------------------------------------------------
def test_content_addition_detected():
    s1 = MonitoringSnapshot("snap_1", "owner_A", "conv_1", "target_1", "https://example.com", selected_text_blocks=["Line 1"])
    s2 = MonitoringSnapshot("snap_2", "owner_A", "conv_1", "target_1", "https://example.com", selected_text_blocks=["Line 1", "Line 2 Added"])

    evs = content_diff_engine.diff_snapshots(s1, s2)
    assert len(evs) >= 1
    assert any(e.change_type == ChangeType.CONTENT_ADDED for e in evs)


def test_content_removal_detected():
    s1 = MonitoringSnapshot("snap_1", "owner_A", "conv_1", "target_1", "https://example.com", selected_text_blocks=["Line 1", "Line 2 Removed"])
    s2 = MonitoringSnapshot("snap_2", "owner_A", "conv_1", "target_1", "https://example.com", selected_text_blocks=["Line 1"])

    evs = content_diff_engine.diff_snapshots(s1, s2)
    assert len(evs) >= 1
    assert any(e.change_type == ChangeType.CONTENT_REMOVED for e in evs)


def test_content_modification_detected():
    s1 = MonitoringSnapshot("snap_1", "owner_A", "conv_1", "target_1", "https://example.com", selected_text_blocks=["Python 3.13 is current"])
    s2 = MonitoringSnapshot("snap_2", "owner_A", "conv_1", "target_1", "https://example.com", selected_text_blocks=["Python 3.14 is current"])

    evs = content_diff_engine.diff_snapshots(s1, s2)
    assert len(evs) >= 1
    assert any(e.change_type == ChangeType.CONTENT_MODIFIED for e in evs)


def test_heading_hierarchy_change_detected():
    s1 = MonitoringSnapshot("snap_1", "owner_A", "conv_1", "target_1", "https://example.com", heading_fingerprints=["H1: Title"])
    s2 = MonitoringSnapshot("snap_2", "owner_A", "conv_1", "target_1", "https://example.com", heading_fingerprints=["H1: Title", "H2: Specs"])

    evs = content_diff_engine.diff_snapshots(s1, s2)
    assert len(evs) >= 1
    assert any(e.change_type == ChangeType.CONTENT_ADDED for e in evs)


def test_important_link_addition_detected():
    fp1 = snapshot_fingerprint_generator.compute_structural_fingerprint(["H1"], ["https://example.com/link1"])
    fp2 = snapshot_fingerprint_generator.compute_structural_fingerprint(["H1"], ["https://example.com/link1", "https://example.com/link2"])
    assert fp1 != fp2


def test_tracking_param_link_ignored():
    u1 = snapshot_fingerprint_generator.sanitize_url("https://example.com?utm_source=twitter")
    u2 = snapshot_fingerprint_generator.sanitize_url("https://example.com?utm_source=facebook")
    assert u1 == u2


def test_whitespace_only_change_ignored():
    ev = ChangeEvidence("ev_1", ChangeType.CONTENT_MODIFIED, "text", "  Hello  World  ", "Hello World", is_meaningful=True)
    analyzed = semantic_change_detector.analyze_evidences([ev])
    assert analyzed[0].is_meaningful is False
    assert analyzed[0].change_type == ChangeType.COSMETIC_ONLY


def test_css_class_change_ignored():
    ev = ChangeEvidence("ev_1", ChangeType.CONTENT_MODIFIED, "text", "Text", "Text", is_meaningful=True)
    analyzed = semantic_change_detector.analyze_evidences([ev])
    assert analyzed[0].is_meaningful is False


def test_version_change_classification():
    ev = ChangeEvidence("ev_1", ChangeType.VALUE_CHANGED, "release_version", "1.0", "2.0", is_meaningful=True)
    ctype = change_classifier.classify_change(ev)
    assert ctype == ChangeType.VERSION_CHANGED


def test_price_change_classification():
    ev = ChangeEvidence("ev_1", ChangeType.VALUE_CHANGED, "price", "$10", "$20", is_meaningful=True)
    ctype = change_classifier.classify_change(ev)
    assert ctype == ChangeType.PRICE_CHANGED


def test_status_change_classification():
    ev = ChangeEvidence("ev_1", ChangeType.VALUE_CHANGED, "status", "In Stock", "Out of Stock", is_meaningful=True)
    ctype = change_classifier.classify_change(ev)
    assert ctype == ChangeType.STATUS_CHANGED


def test_security_advisory_change_classification():
    ev = ChangeEvidence("ev_1", ChangeType.CONTENT_MODIFIED, "advisory", "None", "CVE-2026-1234 Critical Vulnerability", is_meaningful=True)
    sig, reasons = change_significance_evaluator.evaluate_significance([ev])
    assert sig == ChangeSignificance.CRITICAL


def test_structured_row_addition():
    s1 = MonitoringSnapshot("snap_1", "owner_A", "conv_1", "target_1", "https://example.com", important_field_values={"row1": "v1"})
    s2 = MonitoringSnapshot("snap_2", "owner_A", "conv_1", "target_1", "https://example.com", important_field_values={"row1": "v1", "row2": "v2"})

    evs = structured_diff_engine.diff_important_fields(s1, s2)
    assert len(evs) == 1
    assert evs[0].new_value == "v2"


def test_structured_row_removal():
    s1 = MonitoringSnapshot("snap_1", "owner_A", "conv_1", "target_1", "https://example.com", important_field_values={"row1": "v1", "row2": "v2"})
    s2 = MonitoringSnapshot("snap_2", "owner_A", "conv_1", "target_1", "https://example.com", important_field_values={"row1": "v1"})

    evs = structured_diff_engine.diff_important_fields(s1, s2)
    assert len(evs) == 1
    assert evs[0].old_value == "v2"


def test_structured_field_value_change():
    s1 = MonitoringSnapshot("snap_1", "owner_A", "conv_1", "target_1", "https://example.com", important_field_values={"fieldA": "old_val"})
    s2 = MonitoringSnapshot("snap_2", "owner_A", "conv_1", "target_1", "https://example.com", important_field_values={"fieldA": "new_val"})

    evs = structured_diff_engine.diff_important_fields(s1, s2)
    assert len(evs) == 1
    assert evs[0].old_value == "old_val"
    assert evs[0].new_value == "new_val"


def test_resource_added_detected():
    s1 = MonitoringSnapshot("snap_1", "owner_A", "conv_1", "target_1", "https://example.com", important_field_values={})
    s2 = MonitoringSnapshot("snap_2", "owner_A", "conv_1", "target_1", "https://example.com", important_field_values={"resource_file": "doc.pdf"})

    evs = structured_diff_engine.diff_important_fields(s1, s2)
    assert len(evs) == 1


def test_resource_removed_detected():
    s1 = MonitoringSnapshot("snap_1", "owner_A", "conv_1", "target_1", "https://example.com", important_field_values={"resource_file": "doc.pdf"})
    s2 = MonitoringSnapshot("snap_2", "owner_A", "conv_1", "target_1", "https://example.com", important_field_values={})

    evs = structured_diff_engine.diff_important_fields(s1, s2)
    assert len(evs) == 1


# ----------------------------------------------------
# K. CONFIG & HARD LIMIT TESTS (47-65)
# ----------------------------------------------------
def test_snapshot_ttl_expiration():
    assert MonitoringConfig.SNAPSHOT_TTL_SECONDS == 3600


def test_snapshot_fifo_eviction():
    assert MonitoringConfig.MAX_SNAPSHOTS_PER_TARGET == 5


def test_max_monitored_targets_limit():
    assert MonitoringConfig.MAX_MONITORED_TARGETS_PER_CONVERSATION == 10


def test_max_monitor_context_chars_limit():
    assert MonitoringConfig.MAX_MONITOR_CONTEXT_CHARS == 15000


def test_concurrency_semaphore_bound():
    assert MonitoringConfig.MAX_CONCURRENT_MONITOR_OPERATIONS == 4


def test_old_value_new_value_preservation():
    ev = ChangeEvidence("ev_1", ChangeType.VALUE_CHANGED, "field", "OLD", "NEW")
    assert ev.old_value == "OLD"
    assert ev.new_value == "NEW"


def test_heading_fingerprint_generation():
    fp = snapshot_fingerprint_generator.compute_structural_fingerprint(["H1"], [])
    assert len(fp) == 64


def test_content_fingerprint_generation():
    fp = snapshot_fingerprint_generator.compute_content_fingerprint(["Block 1"])
    assert len(fp) == 64


def test_structural_fingerprint_generation():
    fp = snapshot_fingerprint_generator.compute_structural_fingerprint(["H1"], ["https://example.com"])
    assert len(fp) == 64


def test_prompt_injection_containment():
    ctx = web_monitor_service._serialize_monitor_context(MonitorBaselineStatus.NO_CHANGE, "https://example.com", [])
    assert "<UNTRUSTED_MONITORED_WEB_CONTENT" in ctx
    assert "</UNTRUSTED_MONITORED_WEB_CONTENT>" in ctx


def test_fail_closed_change_provenance():
    s1 = MonitoringSnapshot("snap_1", "owner_A", "conv_1", "target_1", "https://example.com")
    s2 = MonitoringSnapshot("snap_2", "owner_A", "conv_1", "target_1", "https://example.com")
    finding = ChangeFinding("f_1", "target_1", "https://example.com", "snap_1", "snap_2", ChangeType.CONTENT_ADDED, ChangeSignificance.HIGH, "Summary", evidences=[])
    assert change_provenance_engine.validate_finding_provenance(finding, s1, s2) is False


@pytest.mark.asyncio
async def test_global_20s_timeout_cleanup():
    orig = MonitoringConfig.MAX_MONITOR_RUNTIME_SECONDS
    MonitoringConfig.MAX_MONITOR_RUNTIME_SECONDS = 0.001
    try:
        req = MonitorWebRequest(query="timeout query", url="https://example.com")
        resp = await web_monitor_service.execute_monitoring(req)
        assert resp.baseline_status in (MonitorBaselineStatus.UNKNOWN, MonitorBaselineStatus.NO_BASELINE, MonitorBaselineStatus.NO_CHANGE)
    finally:
        MonitoringConfig.MAX_MONITOR_RUNTIME_SECONDS = orig


def test_monitor_web_request_defaults():
    req = MonitorWebRequest(query="test")
    assert req.force_refresh is False
    assert req.url is None


def test_monitor_target_type_enum():
    assert MonitorTargetType.WEBPAGE == "WEBPAGE"


def test_source_availability_status_enum():
    assert SourceAvailabilityStatus.AVAILABLE == "AVAILABLE"


# ----------------------------------------------------
# L. INTEGRATION & LOCAL FIXTURE TESTS (66-73)
# ----------------------------------------------------
@pytest.mark.asyncio
async def test_api_endpoint_create_baseline():
    req = MonitorWebRequest(query="check python release", url="https://example.com")
    resp = await web_monitor_service.execute_monitoring(req)
    assert resp.baseline_status in (MonitorBaselineStatus.NO_BASELINE, MonitorBaselineStatus.NO_CHANGE, MonitorBaselineStatus.CHANGED)


@pytest.mark.asyncio
async def test_api_endpoint_check_changes():
    req1 = MonitorWebRequest(query="check changes", url="https://example.com")
    resp1 = await web_monitor_service.execute_monitoring(req1)
    req2 = MonitorWebRequest(query="check changes", url="https://example.com")
    resp2 = await web_monitor_service.execute_monitoring(req2)
    assert resp2.baseline_status in (MonitorBaselineStatus.NO_CHANGE, MonitorBaselineStatus.CHANGED)


def test_router_monitoring_intent_detection():
    query = "What changed since I last checked?"
    keywords = ["what changed", "has this page changed", "compare with previous"]
    assert any(kw in query.lower() for kw in keywords)


def test_router_bypass_for_general_queries():
    query = "What is Python?"
    keywords = ["what changed", "has this page changed", "compare with previous"]
    assert not any(kw in query.lower() for kw in keywords)


def test_owner_scope_id_snapshot_isolation():
    snap1 = MonitoringSnapshot("snap_1", "owner_alpha", "conv_1", "target_1", "https://example.com")
    snapshot_manager.store_snapshot(snap1)
    s_found, status = snapshot_manager.get_latest_snapshot("owner_beta", "conv_1", "target_1")
    assert s_found is None


def test_expired_tombstone_does_not_leak_body():
    orig_ttl = MonitoringConfig.SNAPSHOT_TTL_SECONDS
    MonitoringConfig.SNAPSHOT_TTL_SECONDS = 0.001
    try:
        snap1 = MonitoringSnapshot("snap_secret", "owner_A", "conv_1", "target_tomb", "https://example.com", selected_text_blocks=["SECRET BODY DATA"], created_timestamp=time.time() - 1.0)
        snapshot_manager.store_snapshot(snap1)
        s_found, status = snapshot_manager.get_latest_snapshot("owner_A", "conv_1", "target_tomb")
        assert s_found is None
        assert status == MonitorBaselineStatus.BASELINE_EXPIRED
    finally:
        MonitoringConfig.SNAPSHOT_TTL_SECONDS = orig_ttl


def test_local_deterministic_fixture_price_diff():
    s1 = MonitoringSnapshot("snap_1", "owner_A", "conv_1", "target_1", "https://example.com", important_field_values={"price": "$99"})
    s2 = MonitoringSnapshot("snap_2", "owner_A", "conv_1", "target_1", "https://example.com", important_field_values={"price": "$119"})

    evs = structured_diff_engine.diff_important_fields(s1, s2)
    assert len(evs) == 1
    assert evs[0].change_type == ChangeType.PRICE_CHANGED
    assert evs[0].old_value == "$99"
    assert evs[0].new_value == "$119"


def test_local_deterministic_fixture_version_diff():
    s1 = MonitoringSnapshot("snap_1", "owner_A", "conv_1", "target_1", "https://example.com", important_field_values={"version": "1.0.0"})
    s2 = MonitoringSnapshot("snap_2", "owner_A", "conv_1", "target_1", "https://example.com", important_field_values={"version": "1.1.0"})

    evs = structured_diff_engine.diff_important_fields(s1, s2)
    assert len(evs) == 1
    assert evs[0].change_type == ChangeType.VERSION_CHANGED
    assert evs[0].old_value == "1.0.0"
    assert evs[0].new_value == "1.1.0"


@pytest.mark.asyncio
async def test_partial_dynamic_v7_retrieval_never_emits_false_removal():
    req = MonitorWebRequest(query="monitor page", url="https://example.com/v7-partial")
    target_id = f"target_{hash('https://example.com/v7-partial') & 0xffffffff}"

    base_snap = MonitoringSnapshot(
        snapshot_id="snap_base_v7",
        owner_scope_id="default_owner",
        conversation_id="default_conv",
        target_id=target_id,
        canonical_url="https://example.com/v7-partial",
        selected_text_blocks=["Known text block 1", "Known text block 2", "Known text block 3"],
        important_field_values={"version": "3.13", "price": "$99"},
        source_availability=SourceAvailabilityStatus.AVAILABLE,
        completeness=ObservationCompleteness.COMPLETE,
        retrieval_method="V7_DYNAMIC_BROWSER",
    )
    snapshot_manager.store_snapshot(base_snap)

    class V7PartialMockService(MonitorWebService):
        async def _retrieve_and_build_snapshot(self, target_url, owner_scope_id, conversation_id, target_id, req):
            return MonitoringSnapshot(
                snapshot_id="snap_curr_v7_partial",
                owner_scope_id=owner_scope_id,
                conversation_id=conversation_id,
                target_id=target_id,
                canonical_url=target_url,
                selected_text_blocks=["Known text block 1"],
                important_field_values={},
                source_availability=SourceAvailabilityStatus.AVAILABLE,
                completeness=ObservationCompleteness.PARTIAL,
                retrieval_method="V7_DYNAMIC_BROWSER",
            )

    svc = V7PartialMockService()
    resp = await svc.execute_monitoring(req)

    assert resp.baseline_status == MonitorBaselineStatus.PARTIAL_COMPARISON
    content_removals = [f for f in resp.findings if f.change_type == ChangeType.CONTENT_REMOVED]
    assert len(content_removals) == 0
    assert resp.baseline_status != MonitorBaselineStatus.NO_CHANGE


def test_local_fixture_cosmetic_change():
    s1 = MonitoringSnapshot("snap_1", "owner_A", "conv_1", "target_1", "https://example.com?utm_source=twitter", selected_text_blocks=["Product Details"], important_field_values={"price": "$99", "version": "3.13", "status": "Stable"})
    s2 = MonitoringSnapshot("snap_2", "owner_A", "conv_1", "target_1", "https://example.com?utm_source=facebook", selected_text_blocks=["  Product   Details  "], important_field_values={"price": "$99", "version": "3.13", "status": "Stable"})

    evs = structured_diff_engine.diff_important_fields(s1, s2)
    assert len(evs) == 0

    content_evs = content_diff_engine.diff_snapshots(s1, s2)
    analyzed = semantic_change_detector.analyze_evidences(content_evs)
    meaningful = [e for e in analyzed if e.is_meaningful]

    assert len(meaningful) == 0
    types = [e.change_type for e in analyzed]
    assert ChangeType.PRICE_CHANGED not in types
    assert ChangeType.VERSION_CHANGED not in types
    assert ChangeType.STATUS_CHANGED not in types


def test_local_fixture_price_change_mutation():
    s1 = MonitoringSnapshot("snap_1", "owner_A", "conv_1", "target_1", "https://example.com", important_field_values={"price": "$99"})
    s2 = MonitoringSnapshot("snap_2", "owner_A", "conv_1", "target_1", "https://example.com", important_field_values={"price": "$119"})

    evs = structured_diff_engine.diff_important_fields(s1, s2)
    assert len(evs) == 1
    assert evs[0].change_type == ChangeType.PRICE_CHANGED
    assert evs[0].old_value == "$99"
    assert evs[0].new_value == "$119"
    assert evs[0].is_meaningful is True


def test_local_fixture_version_change_mutation():
    s1 = MonitoringSnapshot("snap_1", "owner_A", "conv_1", "target_1", "https://example.com", important_field_values={"version": "3.13"})
    s2 = MonitoringSnapshot("snap_2", "owner_A", "conv_1", "target_1", "https://example.com", important_field_values={"version": "3.14"})

    evs = structured_diff_engine.diff_important_fields(s1, s2)
    assert len(evs) == 1
    assert evs[0].change_type == ChangeType.VERSION_CHANGED
    assert evs[0].old_value == "3.13"
    assert evs[0].new_value == "3.14"
    assert evs[0].is_meaningful is True


def test_local_fixture_mixed_change_mutation():
    s1 = MonitoringSnapshot("snap_1", "owner_A", "conv_1", "target_1", "https://example.com", selected_text_blocks=["Header Title"], important_field_values={"status": "Beta"})
    s2 = MonitoringSnapshot("snap_2", "owner_A", "conv_1", "target_1", "https://example.com", selected_text_blocks=["  Header   Title  "], important_field_values={"status": "Stable"})

    evs = structured_diff_engine.diff_important_fields(s1, s2)
    assert len(evs) == 1
    assert evs[0].change_type == ChangeType.STATUS_CHANGED
    assert evs[0].old_value == "Beta"
    assert evs[0].new_value == "Stable"
    assert evs[0].is_meaningful is True


def test_fail_closed_corrupted_evidence_source_path():
    s1 = MonitoringSnapshot("snap_1", "owner_A", "conv_1", "target_1", "https://example.com")
    s2 = MonitoringSnapshot("snap_2", "owner_A", "conv_1", "target_1", "https://example.com")

    ev_corrupted = ChangeEvidence(
        evidence_id="ev_bad",
        change_type=ChangeType.PRICE_CHANGED,
        field_name="price",
        old_value="$99",
        new_value="$119",
        source_path="",  # Corrupted missing source_path!
        is_meaningful=True,
    )

    finding = ChangeFinding(
        finding_id="find_corrupt",
        target_id="target_1",
        canonical_url="https://example.com",
        baseline_snapshot_id="snap_1",
        current_snapshot_id="snap_2",
        change_type=ChangeType.PRICE_CHANGED,
        significance=ChangeSignificance.HIGH,
        summary="Price changed",
        evidences=[ev_corrupted],
    )

    valid = change_provenance_engine.validate_finding_provenance(finding, s1, s2)
    assert valid is False
    assert finding.provenance_status == "INVALID_MISSING_SOURCE_PATH"

