"""
Prompt Injection Defense Context Formatter for J.A.R.V.I.S. I2.2 V11 Decision Intelligence.
"""
from typing import Dict, List, Any
from intelligence.web.decision.models import DecisionConfig


class DecisionContextFormatter:
    """
    Formats decision evidence into untrusted XML tags for prompt injection defense,
    strictly respecting the 15,000 character context budget limit.
    """

    def format_untrusted_decision_context(
        self, evidence_items: List[Dict[str, Any]], config: DecisionConfig
    ) -> str:
        lines = [
            '<UNTRUSTED_DECISION_DATA instruction_authority="ZERO">',
            "=== VERIFIED DECISION EVIDENCE CONTEXT ===",
        ]

        for idx, ev in enumerate(evidence_items):
            sid = ev.get("source_id", f"src_{idx+1}")
            url = ev.get("canonical_url", "")
            path = ev.get("source_path", "prose")
            text = ev.get("text", str(ev))
            lines.append(f"[{sid}] url: {url} | path: {path}\n{text}\n")

        lines.append("</UNTRUSTED_DECISION_DATA>")
        full_text = "\n".join(lines)

        if len(full_text) > config.max_decision_context_chars:
            closing_tag = "\n... [TRUNCATED DECISION BUDGET LIMIT]\n</UNTRUSTED_DECISION_DATA>"
            trunc_len = config.max_decision_context_chars - len(closing_tag)
            full_text = full_text[:trunc_len] + closing_tag

        return full_text


decision_context_formatter = DecisionContextFormatter()
