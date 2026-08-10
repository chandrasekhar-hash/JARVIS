"""
Coverage Analyzer for J.A.R.V.I.S. I2.2 V5.
Tracks sub-question coverage derived strictly from structural evidence relationships.
No fake numeric confidence percentages.
"""

from typing import List, Dict, Set
from intelligence.web.research.models import EvidenceItem, ResearchSource
from intelligence.web.deep_research.models import QuestionCoverage, QuestionCoverageState


class CoverageAnalyzer:
    """Analyzes evidence coverage per research sub-question."""

    def analyze_coverage(
        self,
        sub_questions: List[str],
        evidence_items: List[EvidenceItem],
        sources: List[ResearchSource],
        conflicts: List[dict]
    ) -> List[QuestionCoverage]:
        """
        Derives structural coverage status per research question.
        Returns List[QuestionCoverage].
        """
        coverage_list: List[QuestionCoverage] = []
        conflict_subqs = {c.get("sub_question_id", "sub_q1") for c in conflicts}

        # Map evidence to sub-questions
        ev_by_subq: Dict[str, List[EvidenceItem]] = {}
        for ev in evidence_items:
            subq = getattr(ev, "sub_question_id", "sub_q1")
            ev_by_subq.setdefault(subq, []).append(ev)

        source_map = {s.source_id: s for s in sources}

        for idx, q_text in enumerate(sub_questions):
            sq_id = f"sub_q{idx + 1}"
            ev_list = ev_by_subq.get(sq_id, [])

            # Extract primary sources supporting this question
            primary_src_ids = []
            for ev in ev_list:
                src = source_map.get(ev.source_id)
                if src and (src.suitability.is_primary_source or src.suitability.is_official):
                    primary_src_ids.append(src.source_id)

            unique_src_count = len({ev.source_id for ev in ev_list})

            # Derive state from structural evidence relationships
            if sq_id in conflict_subqs:
                state = QuestionCoverageState.CONTRADICTED
            elif unique_src_count >= 2:
                state = QuestionCoverageState.SUPPORTED
            elif unique_src_count == 1:
                state = QuestionCoverageState.PARTIALLY_SUPPORTED
            else:
                state = QuestionCoverageState.NO_EVIDENCE

            cov = QuestionCoverage(
                sub_question_id=sq_id,
                question_text=q_text,
                coverage_state=state,
                evidence_ids=[e.evidence_id for e in ev_list],
                primary_sources=list(set(primary_src_ids))
            )
            coverage_list.append(cov)

        return coverage_list


coverage_analyzer = CoverageAnalyzer()
