"""
Web Search Intelligence API Router for J.A.R.V.I.S. I2.2 V1.
Provides POST /api/web/search endpoint for explicit web search queries.
"""
import logging
from fastapi import APIRouter, HTTPException, Request

from intelligence.web.models import (
    WebSearchRequest,
    WebSearchResponse,
    WebPageRequest,
    WebRetrievalResponse,
)
from intelligence.web.search_service import web_search_service
from tools.telemetry import log_structured, backend_log


router = APIRouter(prefix="/api/web", tags=["Web Search Intelligence"])
logger = logging.getLogger("JARVIS_WebAPI")


@router.post("/search", response_model=WebSearchResponse)
async def search_web(search_req: WebSearchRequest, request: Request):
    """
    Web Search Foundation Endpoint (I2.2 V1).
    Executes intent classification, query planning, provider search, normalization,
    deduplication, and ranking. Returns normalized search results with complete provenance.
    """
    if not search_req.query or not search_req.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")

    try:
        response = await web_search_service.search(
            query=search_req.query,
            max_results=search_req.max_results,
            force_search=search_req.force_search,
            freshness_days=search_req.freshness_days,
        )
        return response
    except Exception as exc:
        log_structured(backend_log, "ERROR", f"[Web API] Search endpoint error: {str(exc)}")
        raise HTTPException(
            status_code=500,
            detail=f"Web search foundation service encountered an error: {str(exc)}"
        )


@router.post("/fetch", response_model=WebRetrievalResponse)
async def fetch_web_page(fetch_req: WebPageRequest, request: Request):
    """
    Webpage Retrieval & Content Intelligence Endpoint (I2.2 V2).
    Executes URL safety validation, stream fetching, content-type detection,
    container-first extraction, structural parsing, evidence chunking, and query selection.
    """
    if not fetch_req.url or not fetch_req.url.strip():
        raise HTTPException(status_code=400, detail="URL string cannot be empty.")

    try:
        from intelligence.web.retrieval_service import web_retrieval_service
        response = await web_retrieval_service.fetch_page(fetch_req)
        return response
    except Exception as exc:
        log_structured(backend_log, "ERROR", f"[Web API] Fetch endpoint error: {str(exc)}")
        raise HTTPException(
            status_code=500,
            detail=f"Webpage retrieval service encountered an error: {str(exc)}"
        )


@router.post("/research")
async def research_web(research_req: Request):
    """
    Multi-Source Research & Evidence Synthesis Endpoint (I2.2 V3).
    Executes intent classification, sub-query research planning, source suitability selection,
    parallel page fetching, agreement/contradiction analysis, fact-checking, and fail-closed synthesis.
    """
    body = await research_req.json()
    query = body.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")

    try:
        from intelligence.web.research import web_research_service, ResearchRequest
        req = ResearchRequest(
            query=query,
            force_research=body.get("force_research", False),
            max_sources=body.get("max_sources", 5),
            max_rounds=body.get("max_rounds", 2)
        )
        response = await web_research_service.execute_research(req)
        return response
    except Exception as exc:
        log_structured(backend_log, "ERROR", f"[Web API] Research endpoint error: {str(exc)}")
        raise HTTPException(
            status_code=500,
            detail=f"Web research service encountered an error: {str(exc)}"
        )


@router.post("/temporal")
async def temporal_web_research(temporal_req: Request):
    """
    Current Events, News & Freshness Intelligence Endpoint (I2.2 V4).
    Executes temporal intent classification, timezone-aware time window resolution,
    primary announcement resolution, story clustering, update detection,
    ephemeral TemporalSnapshotStore diffing, and timeline generation.
    """
    body = await temporal_req.json()
    query = body.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")

    try:
        from intelligence.web.temporal import web_temporal_service, TemporalRequest
        req = TemporalRequest(
            query=query,
            user_timezone=body.get("user_timezone"),
            force_temporal=body.get("force_temporal", False),
            conversation_id=body.get("conversation_id")
        )
        response = await web_temporal_service.execute_temporal_research(req)
        return response
    except Exception as exc:
        log_structured(backend_log, "ERROR", f"[Web API] Temporal endpoint error: {str(exc)}")
        raise HTTPException(
            status_code=500,
            detail=f"Web temporal service encountered an error: {str(exc)}"
        )


@router.post("/deep-research")
async def deep_web_research(deep_req: Request):
    """
    Deep Web Research & Source Discovery Endpoint (I2.2 V5).
    Executes multi-round deep web research, structural evidence gap detection,
    candidate link safety & classification, primary-source escalation,
    deterministic novelty tracking, and provenance-grounded synthesis.
    """
    body = await deep_req.json()
    query = body.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")

    try:
        from intelligence.web.deep_research import web_deep_research_service, DeepResearchRequest
        req = DeepResearchRequest(
            query=query,
            conversation_id=body.get("conversation_id"),
            user_timezone=body.get("user_timezone"),
            max_rounds=body.get("max_rounds", 3),
            force_deep_research=body.get("force_deep_research", False)
        )
        response = await web_deep_research_service.execute_deep_research(req)
        return response
    except Exception as exc:
        log_structured(backend_log, "ERROR", f"[Web API] Deep research endpoint error: {str(exc)}")
        raise HTTPException(
            status_code=500,
            detail=f"Web deep research service encountered an error: {str(exc)}"
        )


@router.post("/structured")
async def structured_web_research(structured_req: Request):
    """
    Structured Web Data & Resource Intelligence Endpoint (I2.2 V6).
    Detects, extracts, normalizes, selects, and validates provenance for machine-readable
    structured data (HTML tables, JSON, JSON-LD, feeds, lists, CSVs, downloadable resources, pagination).
    """
    body = await structured_req.json()
    query = body.get("query", "").strip()
    urls = body.get("urls", [])

    if not query and not urls:
        raise HTTPException(status_code=400, detail="Either query or urls must be provided.")

    try:
        from intelligence.web.structured import web_structured_service, StructuredWebRequest
        req = StructuredWebRequest(
            query=query,
            urls=urls,
            max_records=body.get("max_records", 20),
            allow_resource_discovery=body.get("allow_resource_discovery", True),
            allow_pagination=body.get("allow_pagination", True),
            conversation_id=body.get("conversation_id"),
        )
        response = await web_structured_service.execute_structured_research(req)
        return response
    except Exception as exc:
        log_structured(backend_log, "ERROR", f"[Web API] Structured endpoint error: {str(exc)}")
        raise HTTPException(
            status_code=500,
            detail=f"Structured web service encountered an error: {str(exc)}"
        )


@router.post("/browser")
async def browser_web_research(browser_req: Request):
    """
    Interactive Browser & Dynamic Web Intelligence Endpoint (I2.2 V7).
    Executes dynamic rendering, static-first escalation, fail-closed network interception,
    DOM semantic action classification, element reference fingerprinting, and dynamic content extraction.
    """
    body = await browser_req.json()
    query = body.get("query", "").strip()
    url = body.get("url")

    if not query and not url:
        raise HTTPException(status_code=400, detail="Either query or url must be provided.")

    try:
        from intelligence.web.browser import web_browser_service, BrowserWebRequest
        req = BrowserWebRequest(
            query=query,
            url=url,
            allow_interaction=body.get("allow_interaction", True),
            conversation_id=body.get("conversation_id"),
            user_timezone=body.get("user_timezone"),
        )
        response = await web_browser_service.execute_browser_research(req)
        return response
    except Exception as exc:
        log_structured(backend_log, "ERROR", f"[Web API] Browser endpoint error: {str(exc)}")
        raise HTTPException(
            status_code=500,
            detail=f"Browser web service encountered an error: {str(exc)}"
        )


@router.post("/monitor")
async def monitor_web_research(monitor_req: Request):
    """
    Web Monitoring, Change Detection & Continuous Intelligence Endpoint (I2.2 V8).
    Executes scope-isolated snapshot management, baseline change detection, structured data diffing,
    semantic change classification, explainable significance, and availability state tracking.
    """
    body = await monitor_req.json()
    query = body.get("query", "").strip()
    url = body.get("url")

    if not query and not url:
        raise HTTPException(status_code=400, detail="Either query or url must be provided.")

    try:
        from intelligence.web.monitoring import web_monitor_service, MonitorWebRequest
        req = MonitorWebRequest(
            query=query,
            url=url,
            conversation_id=body.get("conversation_id"),
            owner_scope_id=body.get("owner_scope_id"),
            force_refresh=body.get("force_refresh", False),
            user_timezone=body.get("user_timezone"),
        )
        response = await web_monitor_service.execute_monitoring(req)
        return response
    except Exception as exc:
        log_structured(backend_log, "ERROR", f"[Web API] Monitor endpoint error: {str(exc)}")
        raise HTTPException(
            status_code=500,
            detail=f"Monitor web service encountered an error: {str(exc)}"
        )


@router.post("/knowledge")
async def knowledge_web_research(knowledge_req: Request):
    """
    Web Entity, Relationship & Knowledge Intelligence Endpoint (I2.2 V9).
    Converts grounded evidence from V1-V8 into canonical entities, typed relationships,
    temporal entity states, conflict-aware evidence graphs, and fail-closed provenance structures.
    """
    body = await knowledge_req.json()
    query = body.get("query", "").strip()
    urls = body.get("urls", [])

    if not query and not urls:
        raise HTTPException(status_code=400, detail="Either query or urls must be provided.")

    try:
        from intelligence.web.knowledge import web_knowledge_service, KnowledgeWebRequest
        req = KnowledgeWebRequest(
            query=query,
            urls=urls,
            conversation_id=body.get("conversation_id"),
            owner_scope_id=body.get("owner_scope_id"),
            max_depth=body.get("max_depth", 2),
            user_timezone=body.get("user_timezone"),
            force_refresh=body.get("force_refresh", False),
        )
        response = await web_knowledge_service.execute_knowledge_research(req)
        return response.to_dict()
    except Exception as exc:
        log_structured(backend_log, "ERROR", f"[Web API] Knowledge endpoint error: {str(exc)}")
        raise HTTPException(
            status_code=500,
            detail=f"Knowledge web service encountered an error: {str(exc)}"
        )


@router.post("/verify")
async def verify_web_answer(verify_req: Request):
    """
    Grounded Answer Verification & Citation Intelligence Endpoint (I2.2 V10).
    Verifies draft answers against supplied grounded evidence, parses inline citations,
    checks temporal and entity/relationship consistency, performs single bounded repair,
    sanitizes answers, and verifies final provenance.
    """
    body = await verify_req.json()
    draft_answer = body.get("draft_answer", "").strip()
    evidence_context = body.get("evidence_context", [])

    if not draft_answer:
        raise HTTPException(status_code=400, detail="draft_answer string cannot be empty.")

    try:
        from intelligence.web.verification import web_verification_service, VerificationWebRequest
        req = VerificationWebRequest(
            draft_answer=draft_answer,
            evidence_context=evidence_context,
            query=body.get("query", ""),
            conversation_id=body.get("conversation_id"),
            owner_scope_id=body.get("owner_scope_id"),
            user_timezone=body.get("user_timezone"),
        )
        response = await web_verification_service.verify_answer(req)
        return response.to_dict()
    except Exception as exc:
        log_structured(backend_log, "ERROR", f"[Web API] Verify endpoint error: {str(exc)}")
        raise HTTPException(
            status_code=500,
            detail=f"Verification web service encountered an error: {str(exc)}"
        )


@router.post("/decision")
async def decision_web_research(decision_req: Request):
    """
    Decision, Comparison & Recommendation Intelligence Endpoint (I2.2 V11).
    Converts VERIFIED evidence from V1-V10 layers into grounded comparisons, constraint evaluations,
    trade-off analyses, recommendation stability assessments, and 5-part explainable recommendations.
    """
    body = await decision_req.json()
    query = body.get("query", "").strip()

    if not query:
        raise HTTPException(status_code=400, detail="query string cannot be empty.")

    try:
        from intelligence.web.decision import web_decision_service, DecisionWebRequest
        req = DecisionWebRequest(
            query=query,
            evidence_context=body.get("evidence_context", []),
            verified_evidence_registry=body.get("verified_evidence_registry"),
            conversation_id=body.get("conversation_id"),
            owner_scope_id=body.get("owner_scope_id"),
            decision_session_id=body.get("decision_session_id"),
            user_timezone=body.get("user_timezone"),
        )
        response = await web_decision_service.execute_decision(req)
        return response.to_dict()
    except Exception as exc:
        log_structured(backend_log, "ERROR", f"[Web API] Decision endpoint error: {str(exc)}")
        raise HTTPException(
            status_code=500,
            detail=f"Decision web service encountered an error: {str(exc)}"
        )


