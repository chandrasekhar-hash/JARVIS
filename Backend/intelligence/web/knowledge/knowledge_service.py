"""
Master Web Entity, Relationship & Knowledge Intelligence Service for J.A.R.V.I.S. I2.2 V9.
"""
import time
import uuid
from typing import Dict, List, Optional, Set, Any

from intelligence.web.knowledge.models import (
    CanonicalEntity,
    EntityMention,
    EntityResolutionStatus,
    EvidenceBackedRelationship,
    KnowledgeGraphStats,
    KnowledgeStatus,
    KnowledgeWebRequest,
    KnowledgeWebResponse,
    ProvenanceStatus,
    TemporalMetadata,
)
from intelligence.web.knowledge.entity_extractor import entity_extractor
from intelligence.web.knowledge.entity_normalizer import entity_normalizer
from intelligence.web.knowledge.entity_resolver import entity_resolver
from intelligence.web.knowledge.alias_resolver import alias_resolver
from intelligence.web.knowledge.relationship_extractor import relationship_extractor
from intelligence.web.knowledge.relationship_normalizer import relationship_normalizer
from intelligence.web.knowledge.temporal_entity_state import temporal_entity_state_tracker
from intelligence.web.knowledge.entity_conflict_detector import entity_conflict_detector
from intelligence.web.knowledge.knowledge_graph import BoundedKnowledgeGraph, ServerHardLimits
from intelligence.web.knowledge.graph_selector import graph_selector
from intelligence.web.knowledge.knowledge_provenance import provenance_validator
from intelligence.web.knowledge.knowledge_context import knowledge_context_formatter
from intelligence.web.knowledge.knowledge_policy import knowledge_policy
from intelligence.web.knowledge.knowledge_state import knowledge_state_manager

# Import V1-V8 services for composition
from intelligence.web.search_service import web_search_service
from intelligence.web.retrieval_service import web_retrieval_service
from intelligence.web.research import web_research_service, ResearchRequest
from intelligence.web.temporal import web_temporal_service, TemporalRequest
from intelligence.web.deep_research import web_deep_research_service, DeepResearchRequest
from intelligence.web.structured import web_structured_service, StructuredWebRequest
from intelligence.web.browser import web_browser_service, BrowserWebRequest
from intelligence.web.monitoring import web_monitor_service, MonitorWebRequest
from intelligence.web.models import GroundingStatus


class WebKnowledgeService:
    """
    V9 Knowledge Intelligence Service composing V1-V8 grounded evidence streams.
    """

    async def execute_knowledge_research(
        self, req: KnowledgeWebRequest
    ) -> KnowledgeWebResponse:
        start_time = time.time()
        warnings: List[str] = []

        # 1. Policy & parameter sanitization
        sanitized_req = knowledge_policy.validate_and_sanitize_request(req)
        session_id = f"ksession_{uuid.uuid4().hex[:8]}"

        # 2. Get state session
        session = knowledge_state_manager.get_or_create_session(
            owner_scope_id=sanitized_req.owner_scope_id,
            conversation_id=sanitized_req.conversation_id,
            session_id=session_id,
        )
        graph = session.graph

        # Reset entity resolver per request or session
        entity_resolver.reset()

        # 3. Evidence Collection from V1-V8
        collected_evidence_chunks: List[Dict[str, Any]] = []
        valid_source_ids: Set[str] = set()

        grounding_status = "NONE"

        try:
            # Check V8 continuous monitoring / change findings if query asks about changes
            if "change" in sanitized_req.query.lower() or "updated" in sanitized_req.query.lower():
                m_req = MonitorWebRequest(query=sanitized_req.query)
                m_resp = await web_monitor_service.execute_monitoring(m_req)
                if m_resp.findings:
                    grounding_status = "GROUNDED_V8_MONITOR"
                    for f in m_resp.findings:
                        sid = f"v8_src_{uuid.uuid4().hex[:6]}"
                        valid_source_ids.add(sid)
                        collected_evidence_chunks.append({
                            "source_id": sid,
                            "canonical_url": f.url,
                            "text": f"{f.target_name} change: {f.summary}",
                            "source_type": "V8_MONITOR",
                            "evidence_id": f.finding_id,
                        })

            # Check V7 browser dynamic research if query involves browser/dashboard/dynamic interaction
            if not collected_evidence_chunks:
                is_browser = any(kw in sanitized_req.query.lower() for kw in ["browser", "dashboard", "expand", "render", "click", "interactive"])
                if is_browser:
                    b_req = BrowserWebRequest(query=sanitized_req.query)
                    b_resp = await web_browser_service.execute_browser_research(b_req)
                    if b_resp.serialized_context:
                        grounding_status = "GROUNDED_V7_BROWSER"
                        sid = f"v7_src_{uuid.uuid4().hex[:6]}"
                        valid_source_ids.add(sid)
                        collected_evidence_chunks.append({
                            "source_id": sid,
                            "canonical_url": b_resp.final_url or "https://browser.internal",
                            "text": b_resp.serialized_context,
                            "source_type": "V7_BROWSER",
                            "evidence_id": f"ev_v7_{uuid.uuid4().hex[:6]}",
                        })

            # Check V6 structured web data if query involves specs, pricing, versions, tables
            if not collected_evidence_chunks:
                is_structured = any(kw in sanitized_req.query.lower() for kw in ["specs", "table", "version", "pricing", "dataset", "release"])
                if is_structured:
                    st_req = StructuredWebRequest(query=sanitized_req.query, urls=sanitized_req.urls)
                    st_resp = await web_structured_service.execute_structured_research(st_req)
                    if st_resp.selected_records:
                        grounding_status = "GROUNDED_V6_STRUCTURED"
                        for r in st_resp.selected_records:
                            sid = f"v6_src_{uuid.uuid4().hex[:6]}"
                            valid_source_ids.add(sid)
                            rec_data = r.record_data if hasattr(r, "record_data") else r
                            collected_evidence_chunks.append({
                                "source_id": sid,
                                "canonical_url": r.canonical_url if hasattr(r, "canonical_url") else None,
                                "text": str(rec_data),
                                "structured_record": r.to_dict() if hasattr(r, "to_dict") else r,
                                "source_type": "V6_STRUCTURED",
                                "evidence_id": getattr(r, "record_id", f"rec_{uuid.uuid4().hex[:6]}"),
                            })

            # Check V4 temporal findings if query involves timeline or recent events
            if not collected_evidence_chunks:
                t_req = TemporalRequest(query=sanitized_req.query)
                t_resp = await web_temporal_service.execute_temporal_research(t_req)
                if t_resp.finding and t_resp.finding.summary:
                    grounding_status = "GROUNDED_V4_TEMPORAL"
                    sid = f"v4_src_{uuid.uuid4().hex[:6]}"
                    valid_source_ids.add(sid)
                    collected_evidence_chunks.append({
                        "source_id": sid,
                        "canonical_url": getattr(t_resp.finding, "canonical_url", None),
                        "text": t_resp.finding.summary,
                        "source_type": "V4_TEMPORAL",
                        "evidence_id": f"ev_v4_{uuid.uuid4().hex[:6]}",
                    })

            # Default to V3 Research / V1-V2 Retrieval if no chunks collected yet
            if not collected_evidence_chunks:
                res_req = ResearchRequest(query=sanitized_req.query)
                r_resp = await web_research_service.execute_research(res_req)
                if r_resp.finding and r_resp.finding.summary:
                    grounding_status = "GROUNDED_V3_RESEARCH"
                    sid = f"v3_src_{uuid.uuid4().hex[:6]}"
                    valid_source_ids.add(sid)
                    collected_evidence_chunks.append({
                        "source_id": sid,
                        "canonical_url": getattr(r_resp.finding, "canonical_url", None),
                        "text": r_resp.finding.summary,
                        "source_type": "V3_RESEARCH",
                        "evidence_id": f"ev_v3_{uuid.uuid4().hex[:6]}",
                    })
                else:
                    # Fallback search + fetch
                    search_res = await web_search_service.search(query=sanitized_req.query)
                    if search_res.results:
                        grounding_status = "GROUNDED_V1_V2_SEARCH"
                        for res_item in search_res.results[:3]:
                            sid = f"v1_src_{uuid.uuid4().hex[:6]}"
                            valid_source_ids.add(sid)
                            collected_evidence_chunks.append({
                                "source_id": sid,
                                "canonical_url": res_item.canonical_url or res_item.url,
                                "text": f"{res_item.title}: {res_item.snippet}",
                                "source_type": "V1_SEARCH",
                                "evidence_id": f"ev_v1_{uuid.uuid4().hex[:6]}",
                            })

        except Exception as err:
            warnings.append(f"V1-V8 evidence collection notice: {str(err)}")

        if not collected_evidence_chunks:
            return KnowledgeWebResponse(
                status=KnowledgeStatus.NO_EVIDENCE,
                warnings=warnings + ["No grounded evidence collected from V1-V8."],
                grounding_status="NONE",
            )

        # 4. Entity Extraction & Resolution
        extracted_mentions: List[EntityMention] = []
        for chunk in collected_evidence_chunks:
            if knowledge_policy.check_deadline(start_time):
                warnings.append("Wall-clock execution deadline reached during extraction.")
                break

            if "structured_record" in chunk:
                mentions = entity_extractor.extract_mentions_from_structured(
                    structured_records=[chunk["structured_record"]],
                    source_id=chunk["source_id"],
                    canonical_url=chunk.get("canonical_url"),
                    provenance_status=ProvenanceStatus.VERIFIED,
                )
            else:
                mentions = entity_extractor.extract_mentions_from_text(
                    text=chunk["text"],
                    source_id=chunk["source_id"],
                    canonical_url=chunk.get("canonical_url"),
                    evidence_id=chunk.get("evidence_id"),
                    provenance_status=ProvenanceStatus.VERIFIED,
                )
            extracted_mentions.extend(mentions)

        resolved_entities: List[CanonicalEntity] = []
        valid_entity_ids: Set[str] = set()

        for mention in extracted_mentions:
            entity, status = entity_resolver.merge_or_create(mention)
            # Enforce fail-closed provenance on entity
            prov_status = provenance_validator.validate_entity_provenance(entity, valid_source_ids)
            if prov_status != ProvenanceStatus.REJECTED:
                if graph.add_entity(entity):
                    resolved_entities.append(entity)
                    valid_entity_ids.add(entity.entity_id)

        # 5. Relationship Extraction & Normalization
        extracted_relationships: List[EvidenceBackedRelationship] = []
        for chunk in collected_evidence_chunks:
            if knowledge_policy.check_deadline(start_time):
                break

            rels = relationship_extractor.extract_relationships_from_text(
                text=chunk["text"],
                entities=resolved_entities,
                source_id=chunk["source_id"],
                canonical_url=chunk.get("canonical_url"),
                evidence_id=chunk.get("evidence_id"),
                provenance_status=ProvenanceStatus.VERIFIED,
            )
            extracted_relationships.extend(rels)

        # Normalize relationships and validate provenance
        entity_map = {e.entity_id: e for e in resolved_entities}
        valid_relationships: List[EvidenceBackedRelationship] = []

        for rel in extracted_relationships:
            norm_rel = relationship_normalizer.normalize_relationship(rel, entity_map)
            if norm_rel:
                prov_status, verified_rel = provenance_validator.validate_relationship_provenance(
                    rel=norm_rel,
                    valid_source_ids=valid_source_ids,
                    valid_entity_ids=valid_entity_ids,
                )
                if prov_status != ProvenanceStatus.REJECTED and verified_rel:
                    if graph.add_relationship(verified_rel):
                        valid_relationships.append(verified_rel)

        # 6. Conflict Detection
        rel_conflicts = entity_conflict_detector.detect_relationship_conflicts(valid_relationships)
        conflict_dicts = [c.to_dict() for c in rel_conflicts]

        # 7. Query-Aware Selection & Ranking
        selected_entities, selected_relationships = graph_selector.select_subgraph(
            graph=graph,
            query=sanitized_req.query,
            max_depth=sanitized_req.max_depth,
        )

        # 8. Context Serialization
        serialized_ctx = knowledge_context_formatter.format_untrusted_context(
            entities=selected_entities,
            relationships=selected_relationships,
            conflicts=conflict_dicts,
            temporal_state={},
            evidence=collected_evidence_chunks,
        )

        stats = graph.get_stats()
        stats.total_conflicts = len(conflict_dicts)
        stats.traversal_depth = sanitized_req.max_depth

        return KnowledgeWebResponse(
            status=KnowledgeStatus.SUCCESS,
            entities=selected_entities,
            relationships=selected_relationships,
            conflicts=conflict_dicts,
            temporal_state={},
            evidence=collected_evidence_chunks,
            provenance_status=ProvenanceStatus.VERIFIED,
            serialized_context=serialized_ctx,
            graph_statistics=stats,
            warnings=warnings,
            is_truncated=graph.is_truncated,
            grounding_status=grounding_status,
        )


web_knowledge_service = WebKnowledgeService()
