"""
Source Discovery & Primary-Source Escalation Engine for J.A.R.V.I.S. I2.2 V5.
Discovers primary/official source URLs for escalation and generates targeted follow-up queries.
Every follow-up query MUST trace explicitly to an unresolved gap_id or sub_question_id.
"""

from typing import List, Set, Tuple
from intelligence.web.deep_research.models import (
    DiscoveredLink,
    EvidenceGap,
    LinkCategory
)


class SourceDiscovery:
    """Escalates secondary reports to primary sources and generates targeted gap queries."""

    def select_candidate_links_for_escalation(
        self,
        discovered_links: List[DiscoveredLink],
        visited_urls: Set[str],
        max_select: int = 3
    ) -> List[DiscoveredLink]:
        """
        Selects top eligible candidate links, prioritizing OFFICIAL, PRIMARY_SOURCE, and DOCUMENTATION.
        Rejects links with is_eligible_for_selection = False.
        """
        eligible = [link for link in discovered_links if link.is_eligible_for_selection and link.canonical_url not in visited_urls]

        # Prioritize primary/official categories
        def priority_key(link: DiscoveredLink):
            if link.category in (LinkCategory.OFFICIAL, LinkCategory.PRIMARY_SOURCE):
                return 0
            if link.category == LinkCategory.DOCUMENTATION:
                return 1
            if link.category == LinkCategory.ACADEMIC:
                return 2
            return 3

        eligible.sort(key=priority_key)
        return eligible[:max_select]

    def generate_targeted_gap_queries(
        self,
        gaps: List[EvidenceGap],
        attempted_queries: Set[str],
        max_queries: int = 2
    ) -> List[Tuple[str, str, str]]:
        """
        Generates targeted follow-up search queries linked directly to an unresolved gap_id and sub_question_id.
        Returns List of (query_str, gap_id, sub_question_id).
        Strictly prevents query drift.
        """
        targeted: List[Tuple[str, str, str]] = []

        for gap in gaps:
            if len(targeted) >= max_queries:
                break
            if gap.is_resolved:
                continue

            # Construct targeted query based on gap type
            query_str = f"{gap.target} official documentation release notes"
            if gap.gap_type.value == "MISSING_PRIMARY_SOURCE":
                query_str = f"{gap.target} official announcement primary repository"
            elif gap.gap_type.value == "UNRESOLVED_CONTRADICTION":
                query_str = f"{gap.target} official evidence specification"

            if query_str not in attempted_queries:
                targeted.append((query_str, gap.gap_id, gap.sub_question_id))

        return targeted


source_discovery = SourceDiscovery()
