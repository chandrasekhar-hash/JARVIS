"""
Ephemeral DeepResearchState Manager for J.A.R.V.I.S. I2.2 V5.
Maintains state in RAM with deterministic novelty tracking per round.
No webpage body persistence; zero cross-conversation leakage.
"""

import time
from typing import Set, List, Dict, Optional, Any
from intelligence.web.research.models import EvidenceItem, ResearchSource
from intelligence.web.deep_research.models import (
    DiscoveredLink,
    EvidenceGap,
    ResearchNoveltyDelta
)


class DeepResearchState:
    """Ephemeral RAM state for an active deep research session."""

    def __init__(self, research_id: str, query: str, conversation_id: Optional[str] = None):
        self.research_id = research_id
        self.query = query
        self.conversation_id = conversation_id
        self.sub_questions: List[str] = []
        self.visited_urls: Set[str] = set()
        self.attempted_queries: Set[str] = set()
        self.evidence_items: List[EvidenceItem] = []
        self.sources: List[ResearchSource] = []
        self.discovered_links: List[DiscoveredLink] = []
        self.unresolved_gaps: List[EvidenceGap] = []
        self.contradictions: List[Any] = []
        self.novelty_history: List[ResearchNoveltyDelta] = []
        self.completed_rounds: int = 0
        self.start_time: float = time.time()
        self.urls_discovered_count: int = 0
        self.urls_rejected_count: int = 0

    def record_round_novelty(
        self,
        new_sources_count: int,
        new_evidence_count: int,
        resolved_gaps_count: int,
        new_conflicts_count: int,
        new_primary_sources_count: int
    ) -> ResearchNoveltyDelta:
        """Records deterministic structural novelty delta for current round."""
        self.completed_rounds += 1
        delta = ResearchNoveltyDelta(
            round_index=self.completed_rounds,
            new_independent_sources_count=new_sources_count,
            new_evidence_chunks_count=new_evidence_count,
            resolved_gaps_count=resolved_gaps_count,
            newly_discovered_conflicts_count=new_conflicts_count,
            newly_verified_primary_sources_count=new_primary_sources_count
        )
        self.novelty_history.append(delta)
        return delta

    def is_latest_round_novel(self) -> bool:
        """Returns True if the most recent round produced new structural information."""
        if not self.novelty_history:
            return True
        latest = self.novelty_history[-1]
        return (
            latest.new_independent_sources_count > 0 or
            latest.new_evidence_chunks_count > 0 or
            latest.resolved_gaps_count > 0 or
            latest.newly_discovered_conflicts_count > 0
        )
