"""
Provenance-Grounded Deep Research Synthesizer for J.A.R.V.I.S. I2.2 V5.
Synthesizes multi-round research findings, explicitly preserving contradictions even when official sources exist.
"""

from typing import List, Dict, Any
from intelligence.web.research.models import EvidenceItem, ResearchSource, ResearchClaim
from intelligence.web.deep_research.models import (
    DeepResearchFinding,
    QuestionCoverage,
    StoppingReason
)
from intelligence.web.deep_research.research_state import DeepResearchState


class ResearchSynthesizer:
    """Synthesizes structured DeepResearchFinding from state and evidence."""

    def synthesize(
        self,
        state: DeepResearchState,
        coverage: List[QuestionCoverage],
        stopping_reason: StoppingReason
    ) -> DeepResearchFinding:
        """
        Synthesizes grounded findings distinguishing:
        - Established findings
        - Primary-source statements
        - Independently confirmed findings
        - Conflicting evidence (preserved)
        - Unresolved questions
        - Research limitations
        """
        primary_statements: List[str] = []
        established: List[str] = []
        confirmed: List[str] = []
        conflicts: List[str] = []
        unresolved: List[str] = []
        limitations: List[str] = []

        source_map = {s.source_id: s for s in state.sources}

        # 1. Primary Source Statements & Established Findings
        for src in state.sources:
            if src.suitability.is_primary_source or src.suitability.is_official:
                primary_statements.append(f"[{src.source_id}] Primary Statement ({src.domain}): {src.title}")
            else:
                established.append(f"[{src.source_id}] Secondary Report ({src.domain}): {src.title}")

        # 2. Coverage Analysis
        for cov in coverage:
            if cov.coverage_state.value == "SUPPORTED":
                confirmed.append(f"Sub-question '{cov.question_text}' supported by {len(cov.evidence_ids)} evidence items across independent sources.")
            elif cov.coverage_state.value == "CONTRADICTED":
                conflicts.append(f"Contradictory evidence detected on sub-question '{cov.question_text}'.")
            elif cov.coverage_state.value == "UNRESOLVED":
                unresolved.append(f"Sub-question '{cov.question_text}' remains unresolved.")

        # Preserve Contradictions explicitly
        if state.contradictions:
            for idx, conf in enumerate(state.contradictions):
                conflicts.append(f"Conflict #{idx + 1}: {conf.get('description', 'Disagreement between sources')}")

        # Add Limitations
        limitations.append(f"Research completed in {state.completed_rounds} round(s) with stopping reason: {stopping_reason.value}.")
        limitations.append(f"Total pages fetched: {len(state.visited_urls)}, total candidate links evaluated: {state.urls_discovered_count}.")

        # Formulate structured summary text
        summary_lines = [
            f"J.A.R.V.I.S. Deep Web Research Synthesis (Rounds: {state.completed_rounds}, Stopping Reason: {stopping_reason.value}):\n"
        ]

        if primary_statements:
            summary_lines.append("Primary / Official Source Statements:")
            for ps in primary_statements:
                summary_lines.append(f"- {ps}")
            summary_lines.append("")

        if confirmed:
            summary_lines.append("Independently Confirmed Findings:")
            for cf in confirmed:
                summary_lines.append(f"- {cf}")
            summary_lines.append("")

        if conflicts:
            summary_lines.append("Conflicting Evidence & Disagreements (Preserved):")
            for c in conflicts:
                summary_lines.append(f"- {c}")
            summary_lines.append("")

        if unresolved:
            summary_lines.append("Unresolved Questions:")
            for u in unresolved:
                summary_lines.append(f"- {u}")
            summary_lines.append("")

        summary_lines.append("Research Limitations & Provenance:")
        for lim in limitations:
            summary_lines.append(f"- {lim}")

        summary_text = "\n".join(summary_lines)

        return DeepResearchFinding(
            summary=summary_text,
            established_findings=established,
            primary_source_statements=primary_statements,
            independently_confirmed=confirmed,
            conflicting_evidence=conflicts,
            unresolved_questions=unresolved,
            limitations=limitations
        )


research_synthesizer = ResearchSynthesizer()
