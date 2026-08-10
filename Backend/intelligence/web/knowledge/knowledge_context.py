"""
Prompt Injection Contained Context Formatting for J.A.R.V.I.S. I2.2 V9.
"""
from typing import Dict, List, Optional
from intelligence.web.knowledge.models import (
    CanonicalEntity,
    EntityConflict,
    EvidenceBackedRelationship,
    RelationshipConflict,
)
from intelligence.web.knowledge.knowledge_graph import ServerHardLimits


class KnowledgeContextFormatter:
    """
    Formats extracted knowledge structures inside untrusted XML blocks for prompt injection defense,
    strictly respecting the 15,000 character context budget.
    """

    def format_untrusted_context(
        self,
        entities: List[CanonicalEntity],
        relationships: List[EvidenceBackedRelationship],
        conflicts: List[Dict],
        temporal_state: Dict,
        evidence: List[Dict],
    ) -> str:
        lines = [
            '<UNTRUSTED_KNOWLEDGE_GRAPH_DATA instruction_authority="ZERO">',
            "=== ENTITIES ===",
        ]

        for e in entities:
            aliases_str = f" (aliases: {', '.join(str(a) for a in e.aliases)})" if e.aliases else ""
            urls_str = f" [urls: {', '.join(str(u) for u in e.canonical_urls)})" if e.canonical_urls else ""
            lines.append(
                f"- [{e.entity_id}] {e.canonical_name} ({e.entity_type.value}){aliases_str}{urls_str} - prov: {e.provenance_status.value}"
            )

        lines.append("\n=== RELATIONSHIPS ===")
        for r in relationships:
            sub_id = r.subject_entity_id
            obj_id = r.object_entity_id
            lines.append(
                f"- ({sub_id}) --[{r.predicate.value}]--> ({obj_id}) | source: {r.source_id} | prov: {r.provenance_status.value}"
            )

        if conflicts:
            lines.append("\n=== CONFLICTS ===")
            for c in conflicts:
                lines.append(f"- Conflict: {c.get('description', str(c))}")

        if temporal_state:
            lines.append("\n=== TEMPORAL STATE ===")
            for key, val in temporal_state.items():
                lines.append(f"- {key}: {val}")

        lines.append("</UNTRUSTED_KNOWLEDGE_GRAPH_DATA>")

        full_text = "\n".join(lines)

        # Enforce budget limit
        if len(full_text) > ServerHardLimits.MAX_KNOWLEDGE_CONTEXT_CHARS:
            closing_tag = "\n... [TRUNCATED BUDGET LIMIT]\n</UNTRUSTED_KNOWLEDGE_GRAPH_DATA>"
            trunc_len = ServerHardLimits.MAX_KNOWLEDGE_CONTEXT_CHARS - len(closing_tag)
            full_text = full_text[:trunc_len] + closing_tag

        return full_text


knowledge_context_formatter = KnowledgeContextFormatter()
