"""
J.A.R.V.I.S. Intelligence I2.2 V7 — Browser Web Service.
Main service orchestrator for interactive browser and dynamic web intelligence.
Enforces static-first escalation policy, server concurrency limit (asyncio.Semaphore(2)),
global 25.0s wall-clock timeout, prompt injection containment, fail-closed provenance validation,
and guaranteed browser process cleanup.
"""
import asyncio
import logging
import time
from typing import List, Dict, Any, Optional, Set

from intelligence.web.search_service import web_search_service
from intelligence.web.retrieval_service import web_retrieval_service
from intelligence.web.models import WebPageRequest
from intelligence.web.browser.models import (
    BrowserWebRequest,
    BrowserWebResponse,
    BrowserExecutionStatus,
    BrowserEscalationReason,
    BrowserEvidenceItem,
    BrowserConfig,
)
from intelligence.web.browser.browser_escalation import browser_escalation_policy
from intelligence.web.browser.browser_transport import playwright_transport, BaseBrowserTransport
from intelligence.web.browser.navigation_guard import navigation_guard, NavigationGuard
from intelligence.web.browser.browser_session import EphemeralBrowserSession
from intelligence.web.browser.page_observer import page_observer
from intelligence.web.browser.interaction_planner import interaction_planner
from intelligence.web.browser.interaction_executor import interaction_executor
from intelligence.web.browser.dynamic_content_extractor import dynamic_content_extractor
from intelligence.web.browser.browser_provenance import browser_provenance_engine

logger = logging.getLogger("JARVIS_BrowserWebService")


class BrowserWebService:
    """
    Orchestrates V7 Interactive Browser & Dynamic Web Intelligence pipeline.
    """

    def __init__(self, transport: Optional[BaseBrowserTransport] = None, guard: Optional[NavigationGuard] = None):
        self._transport = transport or playwright_transport
        self._guard = guard or navigation_guard
        self._concurrency_semaphore = asyncio.Semaphore(BrowserConfig.MAX_CONCURRENT_BROWSER_SESSIONS)

    async def execute_browser_research(
        self, req: BrowserWebRequest
    ) -> BrowserWebResponse:
        start_time = time.time()

        # Enforce server concurrency bound
        async with self._concurrency_semaphore:
            try:
                return await asyncio.wait_for(
                    self._run_browser_pipeline(req, start_time),
                    timeout=BrowserConfig.MAX_BROWSER_RUNTIME_SECONDS,
                )
            except asyncio.TimeoutError:
                logger.warning(f"Browser pipeline timed out after {BrowserConfig.MAX_BROWSER_RUNTIME_SECONDS}s")
                latency_ms = (time.time() - start_time) * 1000.0
                return BrowserWebResponse(
                    status=BrowserExecutionStatus.TIMEOUT,
                    escalation_reason=BrowserEscalationReason.NONE,
                    query=req.query,
                    limitations=[f"Operation timed out after {BrowserConfig.MAX_BROWSER_RUNTIME_SECONDS}s"],
                    latency_ms=latency_ms,
                )
            except Exception as exc:
                logger.error(f"Browser pipeline error: {exc}", exc_info=True)
                latency_ms = (time.time() - start_time) * 1000.0
                return BrowserWebResponse(
                    status=BrowserExecutionStatus.EXTRACTION_FAILED,
                    escalation_reason=BrowserEscalationReason.NONE,
                    query=req.query,
                    limitations=[f"Browser pipeline error: {str(exc)}"],
                    latency_ms=latency_ms,
                )

    async def _run_browser_pipeline(
        self, req: BrowserWebRequest, start_time: float
    ) -> BrowserWebResponse:
        target_url = req.url

        # 1. Discover target URL via V1 Search if missing
        if not target_url and req.query:
            search_resp = await web_search_service.search(query=req.query, max_results=1)
            if search_resp.results and search_resp.results[0].url:
                target_url = search_resp.results[0].url

        if not target_url:
            latency_ms = (time.time() - start_time) * 1000.0
            return BrowserWebResponse(
                status=BrowserExecutionStatus.EXTRACTION_FAILED,
                escalation_reason=BrowserEscalationReason.NONE,
                query=req.query,
                limitations=["No valid target URL found"],
                latency_ms=latency_ms,
            )

        # 2. Static-First Escalation Check
        fetch_req = WebPageRequest(url=target_url, query=req.query)
        fetch_resp = await web_retrieval_service.fetch_page(fetch_req)

        static_status = "SUCCESS" if fetch_resp.success else "EMPTY_CONTENT"
        static_content = fetch_resp.document.extracted_text if fetch_resp.document else ""

        should_escalate, esc_reason = browser_escalation_policy.evaluate_escalation(
            query=req.query, static_status=static_status, static_content=static_content
        )

        if not should_escalate and fetch_resp.success:
            logger.info("Static V2 content is sufficient. Bypassing browser escalation.")
            latency_ms = (time.time() - start_time) * 1000.0
            return BrowserWebResponse(
                status=BrowserExecutionStatus.STATIC_CONTENT_SUFFICIENT,
                escalation_reason=BrowserEscalationReason.NONE,
                query=req.query,
                canonical_url=fetch_resp.document.metadata.canonical_url if fetch_resp.document else target_url,
                title=fetch_resp.document.metadata.title if fetch_resp.document else "",
                limitations=["Static V2 content was sufficient; browser not invoked."],
                latency_ms=latency_ms,
            )

        # 3. Browser Execution
        session = EphemeralBrowserSession(self._transport, self._guard)
        evidence_items: List[BrowserEvidenceItem] = []
        interaction_chain: List[str] = [f"open_page('{target_url}')"]
        executed_actions_count = 0

        try:
            main_page = await session.start_session()
            ok, canonical_url, nav_msg = await self._transport.navigate(main_page, target_url)

            if not ok:
                latency_ms = (time.time() - start_time) * 1000.0
                return BrowserWebResponse(
                    status=BrowserExecutionStatus.EXTRACTION_FAILED,
                    escalation_reason=esc_reason,
                    query=req.query,
                    canonical_url=canonical_url,
                    limitations=[f"Initial browser navigation failed: {nav_msg}"],
                    latency_ms=latency_ms,
                )

            # Observe Page
            raw_html = await self._transport.observe_html(main_page)
            obs = page_observer.observe_page(raw_html, canonical_url, title="")

            # Dynamic Content Extraction + V6 Composition
            datasets, records = dynamic_content_extractor.extract_dynamic_content(raw_html, "src_browser_1", canonical_url)

            # Record initial evidence
            item_0 = BrowserEvidenceItem(
                evidence_id="ev_0",
                source_id="src_browser_1",
                canonical_url=canonical_url,
                page_title=obs.title,
                content=obs.visible_text[:2000],
                interaction_chain=list(interaction_chain),
                retrieved_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                source_path="page[0].body",
            )
            evidence_items.append(item_0)

            # Interactive Bounded Loop
            if req.allow_interaction:
                action_plans = interaction_planner.plan_next_actions(req.query, obs, executed_actions_count)

                for plan in action_plans:
                    if executed_actions_count >= BrowserConfig.MAX_BROWSER_ACTIONS:
                        break

                    success, delta, msg = await interaction_executor.execute_action(
                        self._transport, main_page, plan, obs
                    )
                    executed_actions_count += 1
                    interaction_chain.append(f"{plan.action_type.value}({plan.target_element_id or ''}): {msg}")

                    if success and delta != "NO_CHANGE":
                        # Re-observe page post interaction
                        post_html = await self._transport.observe_html(main_page)
                        obs = page_observer.observe_page(post_html, canonical_url, title=obs.title)

                        ev_item = BrowserEvidenceItem(
                            evidence_id=f"ev_{executed_actions_count}",
                            source_id="src_browser_1",
                            canonical_url=canonical_url,
                            page_title=obs.title,
                            content=obs.visible_text[:2000],
                            interaction_chain=list(interaction_chain),
                            retrieved_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            source_path=f"interaction[{executed_actions_count}].body",
                        )
                        evidence_items.append(ev_item)

            # Provenance Validation
            provenance = browser_provenance_engine.validate_provenance(evidence_items)

            # Serialize Context under 15,000 char budget
            serialized_context = self._serialize_browser_context(evidence_items, interaction_chain)

            latency_ms = (time.time() - start_time) * 1000.0

            return BrowserWebResponse(
                status=BrowserExecutionStatus.SUCCESS,
                escalation_reason=esc_reason,
                query=req.query,
                canonical_url=canonical_url,
                title=obs.title,
                evidence_items=evidence_items,
                interaction_chain=interaction_chain,
                serialized_context=serialized_context,
                provenance=provenance,
                limitations=[],
                latency_ms=latency_ms,
            )
        finally:
            await session.close_session()

    def _serialize_browser_context(
        self, items: List[BrowserEvidenceItem], chain: List[str]
    ) -> str:
        lines = ["<UNTRUSTED_BROWSER_CONTENT>"]
        lines.append("INTERACTION CHAIN:")
        for step in chain:
            lines.append(f" -> {step}")

        lines.append("EXTRACTED BROWSER EVIDENCE:")
        for item in items:
            lines.append(f" [{item.evidence_id}] {item.page_title} ({item.canonical_url}):\n{item.content}\n")

        lines.append("</UNTRUSTED_BROWSER_CONTENT>")

        full_text = "\n".join(lines)
        if len(full_text) > BrowserConfig.MAX_BROWSER_CONTEXT_CHARS:
            full_text = full_text[: BrowserConfig.MAX_BROWSER_CONTEXT_CHARS] + "\n...[BROWSER CONTEXT TRUNCATED]\n</UNTRUSTED_BROWSER_CONTENT>"

        return full_text


web_browser_service = BrowserWebService()
