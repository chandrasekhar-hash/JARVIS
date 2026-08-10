"""
Web Search Orchestrator Service for J.A.R.V.I.S. I2.2 V1 Web Search Foundation.

Orchestrates intent classification, query planning, provider search execution,
normalization, deduplication, ranking, bounded result limits, and failure fallback.
"""
import time
import logging
from typing import Optional, List, Dict, Any

import config
from intelligence.web.models import (
    WebSearchRequest,
    WebSearchResponse,
    WebSearchIntent,
    SearchResultItem,
)
from intelligence.web.intent_classifier import intent_classifier
from intelligence.web.query_planner import query_planner
from intelligence.web.providers.duckduckgo_provider import DuckDuckGoSearchProvider
from intelligence.web.result_normalizer import result_normalizer
from intelligence.web.deduplicator import deduplicator
from intelligence.web.result_ranker import result_ranker
from tools.telemetry import log_structured, backend_log

logger = logging.getLogger("JARVIS_WebSearchService")


class WebSearchService:
    """
    Main Web Search Service orchestrator for J.A.R.V.I.S.
    Exposes clean, provider-independent async search method.
    """

    def __init__(self):
        # Default provider (DuckDuckGo zero-key development provider)
        self.default_provider = DuckDuckGoSearchProvider(
            timeout_seconds=getattr(config, "WEB_SEARCH_TIMEOUT_SECONDS", 10.0)
        )

    async def search(
        self,
        query: str,
        max_results: int = 10,
        force_search: bool = False,
        freshness_days: Optional[int] = None
    ) -> WebSearchResponse:
        """
        Executes end-to-end Web Search Foundation pipeline:
        1. Check configuration enablement
        2. Detect web-needed (unless force_search=True)
        3. Classify intent
        4. Plan queries (1-3)
        5. Search provider
        6. Normalize results
        7. Deduplicate items
        8. Rank results (intent-aware + freshness)
        9. Bound output to max_results
        """
        start_time = time.perf_counter()
        retrieved_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Check configuration enablement
        web_enabled = getattr(config, "WEB_SEARCH_ENABLED", True)
        if not web_enabled and not force_search:
            return WebSearchResponse(
                query=query,
                web_needed=False,
                intent=WebSearchIntent.GENERAL,
                planned_queries=[],
                results=[],
                total_results=0,
                retrieved_at=retrieved_at,
                provider=self.default_provider.get_provider_name(),
                latency_ms=0.0,
                freshness_applied=False,
                error="Web search is disabled in configuration.",
            )

        if not query or not query.strip():
            return WebSearchResponse(
                query=query,
                web_needed=False,
                intent=WebSearchIntent.GENERAL,
                planned_queries=[],
                results=[],
                total_results=0,
                retrieved_at=retrieved_at,
                provider=self.default_provider.get_provider_name(),
                latency_ms=0.0,
                freshness_applied=False,
                error="Empty query provided.",
            )

        # 1. Detect if web search is needed
        web_needed = force_search or intent_classifier.detect_web_needed(query)
        if not web_needed:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return WebSearchResponse(
                query=query,
                web_needed=False,
                intent=WebSearchIntent.GENERAL,
                planned_queries=[],
                results=[],
                total_results=0,
                retrieved_at=retrieved_at,
                provider=self.default_provider.get_provider_name(),
                latency_ms=round(elapsed_ms, 2),
                freshness_applied=False,
            )

        # 2. Classify Intent
        intent = intent_classifier.classify_intent(query)
        freshness_required = (
            freshness_days is not None
            or intent in (WebSearchIntent.CURRENT_INFORMATION, WebSearchIntent.NEWS)
        )

        # 3. Plan Queries (1-3 queries)
        planned_queries = query_planner.plan_queries(query, intent)

        # Bounded max_results
        config_max = getattr(config, "WEB_SEARCH_MAX_RESULTS", 10)
        bounded_max_results = min(max_results, config_max)

        raw_results: List[Dict[str, Any]] = []

        try:
            # 4. Search via Provider for planned queries
            for q_plan in planned_queries:
                p_results = await self.default_provider.search(
                    query=q_plan,
                    max_results=bounded_max_results
                )
                if p_results:
                    raw_results.extend(p_results)
                if len(raw_results) >= bounded_max_results * 2:
                    break

            # 5. Normalize
            normalized_items: List[SearchResultItem] = []
            for rank_idx, raw_item in enumerate(raw_results, start=1):
                norm = result_normalizer.normalize(raw_item, rank=rank_idx)
                if norm:
                    normalized_items.append(norm)

            # 6. Deduplicate
            deduped_items = deduplicator.deduplicate(normalized_items)

            # 7. Rank (Intent-Aware + Freshness)
            ranked_items = result_ranker.rank_results(
                results=deduped_items,
                query=query,
                intent=intent,
                freshness_required=freshness_required
            )

            # 8. Bound output limit
            final_results = ranked_items[:bounded_max_results]
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            log_structured(
                backend_log,
                "INFO",
                f"[WebSearchService] Completed search for '{query}' (Intent: {intent.value}, Results: {len(final_results)}) in {elapsed_ms:.2f} ms",
            )

            return WebSearchResponse(
                query=query,
                web_needed=True,
                intent=intent,
                planned_queries=planned_queries,
                results=final_results,
                total_results=len(final_results),
                retrieved_at=retrieved_at,
                provider=self.default_provider.get_provider_name(),
                latency_ms=round(elapsed_ms, 2),
                freshness_applied=freshness_required,
            )

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            log_structured(
                backend_log,
                "ERROR",
                f"[WebSearchService] Unexpected error processing web search for '{query}': {str(exc)}",
            )
            # Return clean failure response without crashing JARVIS
            return WebSearchResponse(
                query=query,
                web_needed=True,
                intent=intent,
                planned_queries=planned_queries,
                results=[],
                total_results=0,
                retrieved_at=retrieved_at,
                provider=self.default_provider.get_provider_name(),
                latency_ms=round(elapsed_ms, 2),
                freshness_applied=freshness_required,
                error=f"Web search service encountered an error: {str(exc)}",
            )


# Global singleton instance
web_search_service = WebSearchService()
