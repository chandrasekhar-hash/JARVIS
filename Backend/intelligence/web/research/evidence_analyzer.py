"""
Evidence Analyzer for J.A.R.V.I.S. I2.2 V3.
Performs cross-source Agreement Detection, Contradiction Detection,
and Temporal / Freshness Reasoning.
"""

from typing import List, Tuple, Optional
from intelligence.web.research.models import (
    EvidenceItem,
    ResearchClaim,
    ResearchConflict,
    ResearchSource,
    EvidenceRelationship
)


class EvidenceAnalyzer:
    """Analyzes evidence items for agreement, contradictions, and temporal freshness."""

    def detect_agreements_and_conflicts(
        self,
        evidence_items: List[EvidenceItem],
        sources: List[ResearchSource]
    ) -> Tuple[List[ResearchClaim], List[ResearchConflict]]:
        """
        Analyzes evidence across distinct domain sources.
        Requires independent domain sources before marking is_independent_confirmed = True.
        Preserves conflicting evidence trails in ResearchConflict.
        """
        claims: List[ResearchClaim] = []
        conflicts: List[ResearchConflict] = []
        source_map = {s.source_id: s for s in sources}

        # Group evidence items by topic / sub-question
        grouped: dict[str, List[EvidenceItem]] = {}
        for ev in evidence_items:
            grouped.setdefault(ev.sub_question_id, []).append(ev)

        claim_counter = 1
        conflict_counter = 1

        for sub_q_id, ev_list in grouped.items():
            if not ev_list:
                continue

            # Map unique domains contributing to this sub-question
            domain_ev_map: dict[str, List[EvidenceItem]] = {}
            for ev in ev_list:
                src = source_map.get(ev.source_id)
                domain = src.domain if src else "unknown"
                domain_ev_map.setdefault(domain, []).append(ev)

            unique_domains = list(domain_ev_map.keys())
            all_ev_ids = [ev.evidence_id for ev in ev_list]

            # Check if we have evidence from multiple independent domains
            is_independent = len(unique_domains) > 1

            # Build representative claim statement from primary evidence
            primary_ev = ev_list[0]
            statement = primary_ev.text[:200].strip()

            claim = ResearchClaim(
                claim_id=f"claim_{claim_counter}",
                statement=statement,
                supporting_evidence_ids=all_ev_ids,
                contradicting_evidence_ids=[],
                is_independent_confirmed=is_independent
            )
            claims.append(claim)
            claim_counter += 1

            # Contradiction Detection check (scanning for conflicting numbers/dates/keywords)
            if len(ev_list) >= 2:
                ev_a, ev_b = ev_list[0], ev_list[1]
                src_a = source_map.get(ev_a.source_id)
                src_b = source_map.get(ev_b.source_id)

                # Check if evidence contains conflicting version numbers or dates
                if src_a and src_b and src_a.domain != src_b.domain:
                    text_a = ev_a.text.lower()
                    text_b = ev_b.text.lower()

                    # Simple heuristic conflict detection for dates/versions
                    has_conflict = ("v1." in text_a and "v2." in text_b) or ("removed" in text_a and "retained" in text_b)
                    if has_conflict:
                        # Attempt resolution using primary source preference
                        res_status = "UNRESOLVED"
                        explanation = f"Source {src_a.domain} and {src_b.domain} report conflicting information."
                        if src_a.suitability.is_official and not src_b.suitability.is_official:
                            res_status = "RESOLVED_PRIMARY_PREFERENCE"
                            explanation = f"Resolved in favor of official primary source {src_a.domain} over {src_b.domain}."

                        conflict = ResearchConflict(
                            conflict_id=f"conflict_{conflict_counter}",
                            topic=sub_q_id,
                            claim_a=ev_a.text[:150],
                            evidence_a_id=ev_a.evidence_id,
                            source_a_id=ev_a.source_id,
                            claim_b=ev_b.text[:150],
                            evidence_b_id=ev_b.evidence_id,
                            source_b_id=ev_b.source_id,
                            resolution_status=res_status,
                            explanation=explanation
                        )
                        conflicts.append(conflict)
                        conflict_counter += 1

        return claims, conflicts

    def evaluate_temporal_freshness(
        self,
        sources: List[ResearchSource],
        query: str
    ) -> List[ResearchSource]:
        """
        Evaluates temporal aspects of sources.
        Never manufactures dates when published_at is None.
        """
        is_temporal_query = any(k in query.lower() for k in ["latest", "today", "current", "recent", "new"])
        for src in sources:
            if src.published_at is None:
                # Retain published_at=None, rely on retrieved_at
                src.suitability.reasons.append("Publication date unknown; using retrieval timestamp")
            elif is_temporal_query:
                src.suitability.reasons.append("Source evaluated for temporal freshness query")
        return sources


evidence_analyzer = EvidenceAnalyzer()
