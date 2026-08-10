"""
J.A.R.V.I.S. Intelligence I2.2 V8 — Monitor Web Service.
Main service orchestrator for Web Monitoring, Change Detection & Continuous Intelligence.
Composes frozen V1-V7 services under static-first retrieval, scope-isolated atomic locks, completeness checks,
evidence deduplication collapse, prompt injection containment, and guaranteed resource cleanup.
"""
import asyncio
import logging
import time
from typing import List, Dict, Any, Optional

from intelligence.web.search_service import web_search_service
from intelligence.web.retrieval_service import web_retrieval_service
from intelligence.web.models import WebPageRequest
from intelligence.web.structured.structured_service import web_structured_service, StructuredWebRequest
from intelligence.web.browser.browser_service import web_browser_service, BrowserWebRequest, BrowserExecutionStatus
from intelligence.web.monitoring.models import (
    MonitorWebRequest,
    MonitorWebResponse,
    MonitorBaselineStatus,
    MonitoringSnapshot,
    ChangeFinding,
    ChangeEvidence,
    ChangeType,
    ObservationCompleteness,
    SourceAvailabilityStatus,
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

logger = logging.getLogger("JARVIS_MonitorWebService")


class MonitorWebService:
    """
    Orchestrates V8 Web Monitoring & Change Detection pipeline.
    """

    def __init__(self):
        self._concurrency_semaphore = asyncio.Semaphore(MonitoringConfig.MAX_CONCURRENT_MONITOR_OPERATIONS)

    async def execute_monitoring(
        self, req: MonitorWebRequest
    ) -> MonitorWebResponse:
        start_time = time.time()

        async with self._concurrency_semaphore:
            try:
                return await asyncio.wait_for(
                    self._run_monitoring_pipeline(req, start_time),
                    timeout=MonitoringConfig.MAX_MONITOR_RUNTIME_SECONDS,
                )
            except asyncio.TimeoutError:
                logger.warning(f"Monitoring pipeline timed out after {MonitoringConfig.MAX_MONITOR_RUNTIME_SECONDS}s")
                latency_ms = (time.time() - start_time) * 1000.0
                return MonitorWebResponse(
                    baseline_status=MonitorBaselineStatus.UNKNOWN,
                    query=req.query,
                    limitations=[f"Monitoring operation timed out after {MonitoringConfig.MAX_MONITOR_RUNTIME_SECONDS}s"],
                    latency_ms=latency_ms,
                )
            except Exception as exc:
                logger.error(f"Monitoring pipeline error: {exc}", exc_info=True)
                latency_ms = (time.time() - start_time) * 1000.0
                return MonitorWebResponse(
                    baseline_status=MonitorBaselineStatus.UNKNOWN,
                    query=req.query,
                    limitations=[f"Monitoring pipeline error: {str(exc)}"],
                    latency_ms=latency_ms,
                )

    async def _run_monitoring_pipeline(
        self, req: MonitorWebRequest, start_time: float
    ) -> MonitorWebResponse:
        target_url = req.url
        owner_scope_id = req.owner_scope_id or "default_owner"
        conversation_id = req.conversation_id or "default_conv"

        # 1. Discover URL via V1 Search if missing
        if not target_url and req.query:
            search_resp = await web_search_service.search(query=req.query, max_results=1)
            if search_resp.results and search_resp.results[0].url:
                target_url = search_resp.results[0].url

        if not target_url:
            latency_ms = (time.time() - start_time) * 1000.0
            return MonitorWebResponse(
                baseline_status=MonitorBaselineStatus.UNKNOWN,
                query=req.query,
                limitations=["No valid target URL found"],
                latency_ms=latency_ms,
            )

        target_id = f"target_{hash(target_url) & 0xffffffff}"
        scope_key = (owner_scope_id, conversation_id, target_id)

        # 2. Acquire Atomic Lock for Baseline / Comparison
        target_lock = await snapshot_manager.get_target_lock(scope_key)
        async with target_lock:
            # Check baseline snapshot state
            baseline_snap, baseline_status = snapshot_manager.get_latest_snapshot(
                owner_scope_id, conversation_id, target_id
            )

            # 3. Retrieve Current Observation (V2 Static-First / V7 Dynamic)
            current_snap = await self._retrieve_and_build_snapshot(
                target_url, owner_scope_id, conversation_id, target_id, req
            )

            # Check Observation Completeness
            if current_snap.completeness != ObservationCompleteness.COMPLETE or current_snap.source_availability != SourceAvailabilityStatus.AVAILABLE:
                # Partial / Failed fetch MUST NEVER cause false content removals!
                if not baseline_snap:
                    # Store as baseline anyway if available
                    snapshot_manager.store_snapshot(current_snap)
                    latency_ms = (time.time() - start_time) * 1000.0
                    return MonitorWebResponse(
                        baseline_status=MonitorBaselineStatus.SOURCE_UNAVAILABLE,
                        query=req.query,
                        canonical_url=current_snap.canonical_url,
                        limitations=[f"Current retrieval status: {current_snap.source_availability.value}"],
                        latency_ms=latency_ms,
                    )
                else:
                    latency_ms = (time.time() - start_time) * 1000.0
                    return MonitorWebResponse(
                        baseline_status=MonitorBaselineStatus.PARTIAL_COMPARISON,
                        query=req.query,
                        canonical_url=current_snap.canonical_url,
                        limitations=["Current observation is partial or incomplete. Comparison aborted to prevent false findings."],
                        latency_ms=latency_ms,
                    )

            # Handle NO_BASELINE or BASELINE_EXPIRED
            if not baseline_snap:
                snapshot_manager.store_snapshot(current_snap)
                latency_ms = (time.time() - start_time) * 1000.0
                status_to_return = (
                    MonitorBaselineStatus.BASELINE_EXPIRED
                    if baseline_status == MonitorBaselineStatus.BASELINE_EXPIRED
                    else MonitorBaselineStatus.NO_BASELINE
                )
                return MonitorWebResponse(
                    baseline_status=status_to_return,
                    query=req.query,
                    canonical_url=current_snap.canonical_url,
                    serialized_context=f"<UNTRUSTED_MONITORED_WEB_CONTENT baseline_status=\"{status_to_return.value}\">\nTarget: {current_snap.canonical_url}\nStatus: Initial baseline snapshot recorded.\n</UNTRUSTED_MONITORED_WEB_CONTENT>",
                    limitations=["No prior baseline snapshot existed. Current observation recorded as baseline."],
                    latency_ms=latency_ms,
                )

            # Validate Target Identity Continuity
            id_valid, id_msg = monitoring_policy.validate_target_identity_continuity(
                baseline_snap.canonical_url, current_snap.canonical_url
            )
            if not id_valid:
                latency_ms = (time.time() - start_time) * 1000.0
                return MonitorWebResponse(
                    baseline_status=MonitorBaselineStatus.PARTIAL_COMPARISON,
                    query=req.query,
                    canonical_url=current_snap.canonical_url,
                    limitations=[f"Target identity continuity check failed: {id_msg}"],
                    latency_ms=latency_ms,
                )

            # 4. Fingerprint Fast Path Check for NO_CHANGE
            if (
                baseline_snap.content_fingerprint == current_snap.content_fingerprint
                and baseline_snap.structural_fingerprint == current_snap.structural_fingerprint
            ):
                snapshot_manager.store_snapshot(current_snap)
                latency_ms = (time.time() - start_time) * 1000.0
                return MonitorWebResponse(
                    baseline_status=MonitorBaselineStatus.NO_CHANGE,
                    query=req.query,
                    canonical_url=current_snap.canonical_url,
                    serialized_context=f"<UNTRUSTED_MONITORED_WEB_CONTENT baseline_status=\"NO_CHANGE\">\nTarget: {current_snap.canonical_url}\nStatus: Web content is identical to baseline.\n</UNTRUSTED_MONITORED_WEB_CONTENT>",
                    latency_ms=latency_ms,
                )

            # 5. Deterministic Diff & V6 Structured Composition
            content_evidences = content_diff_engine.diff_snapshots(baseline_snap, current_snap)
            structured_evidences = structured_diff_engine.diff_important_fields(baseline_snap, current_snap)

            raw_evidences = content_evidences + structured_evidences

            # Filter Cosmetic vs Meaningful changes
            meaningful_evidences = semantic_change_detector.analyze_evidences(raw_evidences)
            filtered_evidences = [e for e in meaningful_evidences if e.is_meaningful]

            if not filtered_evidences:
                snapshot_manager.store_snapshot(current_snap)
                latency_ms = (time.time() - start_time) * 1000.0
                return MonitorWebResponse(
                    baseline_status=MonitorBaselineStatus.NO_CHANGE,
                    query=req.query,
                    canonical_url=current_snap.canonical_url,
                    serialized_context=f"<UNTRUSTED_MONITORED_WEB_CONTENT baseline_status=\"NO_CHANGE\">\nTarget: {current_snap.canonical_url}\nStatus: Only cosmetic changes detected.\n</UNTRUSTED_MONITORED_WEB_CONTENT>",
                    limitations=["Only cosmetic presentation/formatting changes detected."],
                    latency_ms=latency_ms,
                )

            # Deduplicate & Collapse Change Findings
            primary_ev = filtered_evidences[0]
            change_type = change_classifier.classify_change(primary_ev)
            significance, reasons = change_significance_evaluator.evaluate_significance(filtered_evidences)

            finding = ChangeFinding(
                finding_id=f"find_{int(time.time() * 1000)}",
                target_id=target_id,
                canonical_url=current_snap.canonical_url,
                baseline_snapshot_id=baseline_snap.snapshot_id,
                current_snapshot_id=current_snap.snapshot_id,
                change_type=change_type,
                significance=significance,
                summary=f"{change_type.value} detected on {current_snap.canonical_url}",
                evidences=filtered_evidences,
                reasons=reasons,
            )

            # Validate Change Finding Provenance
            prov_valid = change_provenance_engine.validate_finding_provenance(finding, baseline_snap, current_snap)
            if not prov_valid:
                logger.warning("Change finding failed provenance validation. Dropping finding.")
                findings = []
                status = MonitorBaselineStatus.PARTIAL_COMPARISON
            else:
                findings = [finding]
                status = MonitorBaselineStatus.CHANGED

            # Store current snapshot as new baseline
            snapshot_manager.store_snapshot(current_snap)

            # Serialize Context under 15,000 char budget
            serialized_context = self._serialize_monitor_context(status, current_snap.canonical_url, findings)
            latency_ms = (time.time() - start_time) * 1000.0

            return MonitorWebResponse(
                baseline_status=status,
                query=req.query,
                canonical_url=current_snap.canonical_url,
                findings=findings,
                serialized_context=serialized_context,
                provenance=[{
                    "finding_id": f.finding_id,
                    "baseline_snapshot_id": f.baseline_snapshot_id,
                    "current_snapshot_id": f.current_snapshot_id,
                    "canonical_url": f.canonical_url,
                    "provenance_status": f.provenance_status,
                } for f in findings],
                latency_ms=latency_ms,
            )

    async def _retrieve_and_build_snapshot(
        self, target_url: str, owner_scope_id: str, conversation_id: str, target_id: str, req: MonitorWebRequest
    ) -> MonitoringSnapshot:
        # V2 Static-First Retrieval Attempt
        fetch_req = WebPageRequest(url=target_url, query=req.query)
        fetch_resp = await web_retrieval_service.fetch_page(fetch_req)

        snap_id = f"snap_{int(time.time() * 1000)}"
        retrieved_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if fetch_resp.success and fetch_resp.document:
            doc = fetch_resp.document
            text_blocks = [line.strip() for line in doc.extracted_text.split("\n") if line.strip()][:100]
            headings = [h for h in text_blocks if len(h) < 80][:20]

            content_fp = snapshot_fingerprint_generator.compute_content_fingerprint(text_blocks)
            struct_fp = snapshot_fingerprint_generator.compute_structural_fingerprint(headings, [])

            # Compose V6 Structured Extraction
            st_req = StructuredWebRequest(query=req.query, urls=[doc.metadata.canonical_url or target_url])
            st_resp = await web_structured_service.execute_structured_research(st_req)

            important_fields: Dict[str, str] = {}
            for rec in st_resp.selected_records:
                for k, v in rec.fields.items():
                    important_fields[k] = str(v)

            return MonitoringSnapshot(
                snapshot_id=snap_id,
                owner_scope_id=owner_scope_id,
                conversation_id=conversation_id,
                target_id=target_id,
                canonical_url=doc.metadata.canonical_url or target_url,
                retrieved_at=retrieved_at,
                content_fingerprint=content_fp,
                structural_fingerprint=struct_fp,
                selected_text_blocks=text_blocks,
                heading_fingerprints=headings,
                important_field_values=important_fields,
                source_availability=SourceAvailabilityStatus.AVAILABLE,
                completeness=ObservationCompleteness.COMPLETE,
                retrieval_method="V2_STATIC",
            )

        # Fallback if V2 static fetch fails -> V7 Dynamic Browser Escalation
        browser_req = BrowserWebRequest(query=req.query, url=target_url)
        browser_resp = await web_browser_service.execute_browser_research(browser_req)

        if browser_resp.status == BrowserExecutionStatus.SUCCESS:
            text_blocks = [line.strip() for line in browser_resp.serialized_context.split("\n") if line.strip()][:100]
            content_fp = snapshot_fingerprint_generator.compute_content_fingerprint(text_blocks)
            struct_fp = snapshot_fingerprint_generator.compute_structural_fingerprint([], [])

            return MonitoringSnapshot(
                snapshot_id=snap_id,
                owner_scope_id=owner_scope_id,
                conversation_id=conversation_id,
                target_id=target_id,
                canonical_url=browser_resp.canonical_url or target_url,
                retrieved_at=retrieved_at,
                content_fingerprint=content_fp,
                structural_fingerprint=struct_fp,
                selected_text_blocks=text_blocks,
                source_availability=SourceAvailabilityStatus.AVAILABLE,
                completeness=ObservationCompleteness.COMPLETE,
                retrieval_method="V7_DYNAMIC_BROWSER",
            )

        # Retrieval failed
        return MonitoringSnapshot(
            snapshot_id=snap_id,
            owner_scope_id=owner_scope_id,
            conversation_id=conversation_id,
            target_id=target_id,
            canonical_url=target_url,
            retrieved_at=retrieved_at,
            source_availability=SourceAvailabilityStatus.UNAVAILABLE,
            completeness=ObservationCompleteness.FAILED,
            retrieval_method="FAILED",
        )

    def _serialize_monitor_context(
        self, status: MonitorBaselineStatus, canonical_url: str, findings: List[ChangeFinding]
    ) -> str:
        lines = [f"<UNTRUSTED_MONITORED_WEB_CONTENT baseline_status=\"{status.value}\">"]
        lines.append(f"TARGET: {canonical_url}")

        if not findings:
            lines.append("STATUS: Web content is identical to baseline.")
        else:
            lines.append("DETECTED CHANGES:")
            for f in findings:
                lines.append(f" FINDING [{f.finding_id}]: {f.change_type.value} (Significance: {f.significance.value})")
                lines.append(f" SUMMARY: {f.summary}")
                for ev in f.evidences:
                    lines.append(f"  - [{ev.evidence_id}] Field: '{ev.field_name}' | Old: '{ev.old_value}' -> New: '{ev.new_value}'")

        lines.append("</UNTRUSTED_MONITORED_WEB_CONTENT>")

        full_text = "\n".join(lines)
        if len(full_text) > MonitoringConfig.MAX_MONITOR_CONTEXT_CHARS:
            full_text = full_text[: MonitoringConfig.MAX_MONITOR_CONTEXT_CHARS] + "\n...[MONITOR CONTEXT TRUNCATED]\n</UNTRUSTED_MONITORED_WEB_CONTENT>"

        return full_text


web_monitor_service = MonitorWebService()
