"""
Evidence Gap Detector Engine for J.A.R.V.I.S. I2.2 V5.
Structurally detects missing primary sources, single-source claims, unresolved contradictions, and technical documentation gaps.
"""

from typing import List, Dict, Set
from intelligence.web.research.models import EvidenceItem, ResearchSource
from intelligence.web.deep_research.models import EvidenceGap, EvidenceGapType


class EvidenceGapDetector:
    """Structurally analyzes research evidence to identify evidence gaps."""

    def detect_gaps(
        self,
        sub_questions: List[str],
        evidence_items: List[EvidenceItem],
        sources: List[ResearchSource],
        conflicts: List[dict]
    ) -> List[EvidenceGap]:
        """
        Detects structural evidence gaps across sub-questions.
        Returns List[EvidenceGap].
        """
        gaps: List[EvidenceGap] = []
        source_map = {s.source_id: s for s in sources}
        primary_sources = [s for s in sources if s.suitability.is_primary_source or s.suitability.is_official]

        # 1. Missing Primary Source Gap
        if not primary_sources and sources:
            gaps.append(
                EvidenceGap(
                    gap_id="gap_primary_src",
                    gap_type=EvidenceGapType.MISSING_PRIMARY_SOURCE,
                    target=sources[0].title or sources[0].domain,
                    sub_question_id="sub_q1",
                    description="Research relies entirely on secondary reporting; missing official/primary documentation or announcement."
                )
            )

        # 2. Unresolved Contradictions Gap
        for idx, conf in enumerate(conflicts):
            gaps.append(
                EvidenceGap(
                    gap_id=f"gap_conflict_{idx + 1}",
                    gap_type=EvidenceGapType.UNRESOLVED_CONTRADICTION,
                    target=conf.get("topic", "Contradictory Claim"),
                    sub_question_id=conf.get("sub_question_id", "sub_q1"),
                    description=f"Unresolved conflict detected between sources on '{conf.get('topic', 'topic')}'. Needs primary verification."
                )
            )

        # 3. Single Source Claim Gaps
        evidence_per_subq: Dict[str, Set[str]] = {}
        for ev in evidence_items:
            subq = getattr(ev, "sub_question_id", "sub_q1")
            evidence_per_subq.setdefault(subq, set()).add(ev.source_id)

        for sq_id in sub_questions:
            src_set = evidence_per_subq.get(sq_id, set())
            if len(src_set) == 1:
                gaps.append(
                    EvidenceGap(
                        gap_id=f"gap_single_src_{sq_id}",
                        gap_type=EvidenceGapType.ONLY_ONE_INDEPENDENT_SOURCE,
                        target=sq_id,
                        sub_question_id=sq_id,
                        description=f"Sub-question '{sq_id}' supported by only 1 source. Needs independent confirmation."
                    )
                )
            elif len(src_set) == 0:
                gaps.append(
                    EvidenceGap(
                        gap_id=f"gap_no_evidence_{sq_id}",
                        gap_type=EvidenceGapType.UNSUPPORTED_CLAIM,
                        target=sq_id,
                        sub_question_id=sq_id,
                        description=f"Sub-question '{sq_id}' has zero supporting evidence chunks."
                    )
                )

        return gaps


evidence_gap_detector = EvidenceGapDetector()
