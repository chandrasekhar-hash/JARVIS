"""
J.A.R.V.I.S. Intelligence I2.2 V6 — Structured Web Service.
Main service orchestrator for structured web data and resource intelligence.
Runs under a global 20.0s wall-clock deadline with automatic resource cleanup,
provenance validation, context budget enforcement (15,000 chars), and prompt injection containment.
"""
import asyncio
import logging
import time
from typing import List, Dict, Any, Set, Optional

from intelligence.web.search_service import web_search_service
from intelligence.web.retrieval_service import web_retrieval_service
from intelligence.web.models import WebPageRequest
from intelligence.web.structured.models import (
    StructuredWebRequest,
    StructuredWebResponse,
    StructuredExtractionResult,
    StructuredRecord,
    StructuredDataset,
    ResourceCandidate,
    PaginationMetadata,
    StructuredDataType,
    StructuredConfig,
)
from intelligence.web.structured.structured_detector import structured_detector
from intelligence.web.structured.table_extractor import table_extractor
from intelligence.web.structured.json_extractor import json_extractor
from intelligence.web.structured.jsonld_extractor import jsonld_extractor
from intelligence.web.structured.feed_extractor import feed_extractor
from intelligence.web.structured.list_extractor import list_extractor
from intelligence.web.structured.resource_discovery import resource_discovery_service
from intelligence.web.structured.pagination_detector import pagination_detector
from intelligence.web.structured.schema_normalizer import schema_normalizer
from intelligence.web.structured.structured_selector import structured_selector
from intelligence.web.structured.structured_provenance import structured_provenance_engine

logger = logging.getLogger("JARVIS_StructuredWebService")


class StructuredWebService:
    """
    Orchestrates V6 Structured Web Data & Resource Intelligence pipeline.
    """

    async def execute_structured_research(
        self, req: StructuredWebRequest
    ) -> StructuredWebResponse:
        start_time = time.time()

        try:
            return await asyncio.wait_for(
                self._run_structured_pipeline(req, start_time),
                timeout=StructuredConfig.MAX_WALL_CLOCK_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.warning(f"Structured web pipeline timed out after {StructuredConfig.MAX_WALL_CLOCK_SECONDS}s")
            latency_ms = (time.time() - start_time) * 1000.0
            return StructuredWebResponse(
                status="TIMEOUT",
                query=req.query,
                limitations=[f"Operation timed out after {StructuredConfig.MAX_WALL_CLOCK_SECONDS}s"],
                latency_ms=latency_ms,
            )
        except Exception as exc:
            logger.error(f"Structured web pipeline error: {exc}", exc_info=True)
            latency_ms = (time.time() - start_time) * 1000.0
            return StructuredWebResponse(
                status="ERROR",
                query=req.query,
                limitations=[f"Pipeline error: {str(exc)}"],
                latency_ms=latency_ms,
            )

    async def _run_structured_pipeline(
        self, req: StructuredWebRequest, start_time: float
    ) -> StructuredWebResponse:
        urls_to_fetch = list(req.urls)

        # 1. If no URLs provided, use V1 Search to discover target pages
        if not urls_to_fetch and req.query:
            search_resp = await web_search_service.search(query=req.query, max_results=3)
            for res in search_resp.results:
                if res.url:
                    urls_to_fetch.append(res.url)

        urls_to_fetch = urls_to_fetch[: StructuredConfig.MAX_STRUCTURED_PAGES]

        extracted_records: List[StructuredRecord] = []
        extracted_datasets: List[StructuredDataset] = []
        discovered_resources: List[ResourceCandidate] = []
        detected_types: Set[StructuredDataType] = set()
        visited_urls: Set[str] = set()

        pagination_meta: Optional[PaginationMetadata] = None

        # 2. Fetch and process pages
        for page_idx, target_url in enumerate(urls_to_fetch):
            if target_url in visited_urls:
                continue
            visited_urls.add(target_url)

            # Fetch via V2 Safe Retrieval
            fetch_req = WebPageRequest(url=target_url, query=req.query)
            fetch_resp = await web_retrieval_service.fetch_page(fetch_req)

            if not fetch_resp.success or not fetch_resp.document:
                continue

            raw_body = fetch_resp.document.extracted_text or ""
            content_type = fetch_resp.document.metadata.content_type or ""
            source_id = f"src_{page_idx + 1}"
            canonical_url = fetch_resp.document.metadata.canonical_url or target_url

            # Detect formats
            page_types = structured_detector.detect_formats(raw_body, content_type)
            detected_types.update(page_types)

            # Extract HTML Tables
            if StructuredDataType.HTML_TABLE in page_types:
                tables = table_extractor.extract_tables(raw_body, source_id, canonical_url)
                extracted_datasets.extend(tables)
                for ds in tables:
                    extracted_records.extend(ds.records)

            # Extract JSON Bodies
            if StructuredDataType.JSON in page_types:
                json_ds = json_extractor.extract_json(raw_body, source_id, canonical_url)
                extracted_datasets.extend(json_ds)
                for ds in json_ds:
                    extracted_records.extend(ds.records)

            # Extract JSON-LD Markup
            if StructuredDataType.JSON_LD in page_types:
                jsonld_recs = jsonld_extractor.extract_jsonld(raw_body, source_id, canonical_url)
                extracted_records.extend(jsonld_recs)

            # Extract Feeds (RSS / Atom)
            if StructuredDataType.RSS in page_types or StructuredDataType.ATOM in page_types:
                feeds = feed_extractor.extract_feed(raw_body, source_id, canonical_url)
                extracted_datasets.extend(feeds)
                for ds in feeds:
                    extracted_records.extend(ds.records)

            # Extract Semantic Lists
            if StructuredDataType.STRUCTURED_LIST in page_types:
                lists = list_extractor.extract_lists(raw_body, source_id, canonical_url)
                extracted_datasets.extend(lists)
                for ds in lists:
                    extracted_records.extend(ds.records)

            # Resource Discovery (async)
            if req.allow_resource_discovery and StructuredDataType.DOWNLOADABLE_RESOURCE in page_types:
                res_candidates = await resource_discovery_service.discover_resources(raw_body, source_id, canonical_url)
                discovered_resources.extend(res_candidates)

            # Pagination Detection (async)
            if req.allow_pagination and page_idx == 0:
                pagination_meta = await pagination_detector.detect_pagination(raw_body, canonical_url, visited_urls)

        # 3. Schema Normalization
        for record in extracted_records:
            for field in record.fields:
                schema_normalizer.normalize_field(field)

        # 4. Relevant Record Selection
        selected_records = structured_selector.select_relevant_records(req.query, extracted_records)

        # 5. Provenance Validation
        provenance = structured_provenance_engine.validate_provenance(selected_records)

        # 6. Context Serialization under 15,000 char budget
        serialized_context = self._serialize_structured_context(selected_records, extracted_datasets, discovered_resources)

        latency_ms = (time.time() - start_time) * 1000.0

        return StructuredWebResponse(
            status="SUCCESS",
            query=req.query,
            detected_types=list(detected_types),
            selected_records=selected_records,
            datasets=extracted_datasets,
            resources=discovered_resources,
            pagination=pagination_meta,
            serialized_context=serialized_context,
            provenance=provenance,
            limitations=[],
            latency_ms=latency_ms,
        )

    def _serialize_structured_context(
        self,
        records: List[StructuredRecord],
        datasets: List[StructuredDataset],
        resources: List[ResourceCandidate],
    ) -> str:
        lines = ["<UNTRUSTED_STRUCTURED_WEB_DATA>"]

        if datasets:
            lines.append("DATASETS:")
            for ds in datasets:
                lines.append(f" - [{ds.dataset_id}] {ds.title} (Type: {ds.data_type.value}, Columns: {', '.join(ds.columns)})")

        if records:
            lines.append("STRUCTURED RECORDS:")
            for rec in records:
                field_strs = [
                    f"{f.name}={f.value}" + (f" (norm: {f.normalized_value})" if f.normalized_value is not None else "")
                    for f in rec.fields[:10]
                ]
                lines.append(f" Record [{rec.record_id}] ({rec.record_type.value}): {'; '.join(field_strs)}")

        if resources:
            lines.append("DISCOVERED RESOURCES:")
            for res in resources[:10]:
                lines.append(f" Resource: {res.url} (Type: {res.resource_type}, Safe: {res.is_url_safe})")

        lines.append("</UNTRUSTED_STRUCTURED_WEB_DATA>")

        full_text = "\n".join(lines)
        if len(full_text) > StructuredConfig.MAX_STRUCTURED_CONTEXT_CHARS:
            full_text = full_text[: StructuredConfig.MAX_STRUCTURED_CONTEXT_CHARS] + "\n...[STRUCTURED CONTEXT TRUNCATED]\n</UNTRUSTED_STRUCTURED_WEB_DATA>"

        return full_text


web_structured_service = StructuredWebService()
