"""
Research Synthesizer for J.A.R.V.I.S. I2.2 V3.
Enforces MAX_EVIDENCE_CHARS budget (12,000 chars / ~3,000 tokens), formats untrusted boundaries,
and produces grounded answers with claim-level provenance citations.
"""

from typing import List, Tuple
from intelligence.web.research.models import (
    ResearchFinding,
    ResearchClaim,
    ResearchConflict,
    ResearchSource,
    EvidenceItem,
    FactCheckDetail,
    ResearchIntent
)
from intelligence.web.research.planner import MAX_EVIDENCE_CHARS


class ResearchSynthesizer:
    """Synthesizes structured evidence items into a clean, grounded natural-language answer."""

    def select_and_budget_evidence(self, evidence_items: List[EvidenceItem]) -> List[EvidenceItem]:
        """
        Selects relevant evidence items and enforces hard MAX_EVIDENCE_CHARS budget (12,000 chars / ~3,000 tokens).
        """
        budgeted: List[EvidenceItem] = []
        total_chars = 0

        for item in evidence_items:
            item_len = len(item.text)
            if total_chars + item_len > MAX_EVIDENCE_CHARS:
                # Truncate final item to fit budget strictly
                allowed = MAX_EVIDENCE_CHARS - total_chars
                suffix = "... [truncated]"
                if allowed > len(suffix) + 20:
                    text_cutoff = allowed - len(suffix)
                    truncated_item = EvidenceItem(
                        evidence_id=item.evidence_id,
                        source_id=item.source_id,
                        canonical_url=item.canonical_url,
                        heading_path=item.heading_path,
                        text=item.text[:text_cutoff] + suffix,
                        sub_question_id=item.sub_question_id,
                        relationship=item.relationship
                    )
                    budgeted.append(truncated_item)
                break
            budgeted.append(item)
            total_chars += item_len

        return budgeted


    def format_untrusted_evidence_context(
        self,
        evidence_items: List[EvidenceItem],
        sources: List[ResearchSource]
    ) -> str:
        """
        Formats evidence items inside <UNTRUSTED_WEBPAGE_CONTENT> XML boundaries.
        Ensures web data retains zero instructional authority over LLM prompts.
        """
        source_map = {s.source_id: s for s in sources}
        budgeted_items = self.select_and_budget_evidence(evidence_items)

        blocks = []
        for item in budgeted_items:
            src = source_map.get(item.source_id)
            title = src.title if src else "Web Evidence"
            domain = src.domain if src else "unknown"

            heading = " > ".join(item.heading_path) if item.heading_path else "Main"
            block = (
                f'<UNTRUSTED_WEBPAGE_CONTENT source_id="{item.source_id}" evidence_id="{item.evidence_id}" '
                f'url="{item.canonical_url}" domain="{domain}">\n'
                f'Title: {title}\n'
                f'Heading: {heading}\n'
                f'Content:\n{item.text}\n'
                f'</UNTRUSTED_WEBPAGE_CONTENT>'
            )
            blocks.append(block)

        return "\n\n".join(blocks)

    def synthesize_finding(
        self,
        query: str,
        intent: ResearchIntent,
        claims: List[ResearchClaim],
        conflicts: List[ResearchConflict],
        fact_check_detail: Optional[FactCheckDetail],
        sources: List[ResearchSource],
        evidence_items: List[EvidenceItem]
    ) -> ResearchFinding:
        """
        Builds the structured ResearchFinding object.
        """
        source_map = {s.source_id: s for s in sources}
        summary_lines = []

        if fact_check_detail:
            summary_lines.append(f"Fact-Check Verdict: {fact_check_detail.verdict.value}")
            summary_lines.append(f"Claim: {fact_check_detail.user_claim}")
            if fact_check_detail.qualifiers:
                summary_lines.append(f"Key Qualifiers: {', '.join(fact_check_detail.qualifiers)}")
            if fact_check_detail.version_scope:
                summary_lines.append(f"Version Scope: {fact_check_detail.version_scope}")
            summary_lines.append(fact_check_detail.explanation)
        else:
            summary_lines.append(f"Multi-source research synthesis for query: '{query}'")

        if claims:
            summary_lines.append("\nKey Verified Findings:")
            for claim in claims:
                src_tags = []
                for ev_id in claim.supporting_evidence_ids:
                    ev_item = next((e for e in evidence_items if e.evidence_id == ev_id), None)
                    if ev_item and ev_item.source_id in source_map:
                        src_tags.append(f"[{ev_item.source_id}]")

                conf_tag = " (Multi-source confirmed)" if claim.is_independent_confirmed else " (Single-source reported)"
                summary_lines.append(f"- {claim.statement} {' '.join(set(src_tags))}{conf_tag}")

        if conflicts:
            summary_lines.append("\nConflicts & Disagreements Detected:")
            for c in conflicts:
                summary_lines.append(
                    f"- [{c.topic}] {c.explanation} (Source {c.source_a_id} vs Source {c.source_b_id}, Status: {c.resolution_status})"
                )

        summary_text = "\n".join(summary_lines)

        return ResearchFinding(
            summary=summary_text,
            claims=claims,
            conflicts=conflicts,
            fact_check_detail=fact_check_detail
        )


research_synthesizer = ResearchSynthesizer()
