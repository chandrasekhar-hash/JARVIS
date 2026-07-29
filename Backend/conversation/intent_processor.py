"""
Intent Classification Engine for J.A.R.V.I.S. Phase V1.3 Conversation Engine.
Classifies user inputs into QUESTION, COMMAND, FOLLOW_UP, CLARIFICATION, or CONTINUATION.
"""
import re
from typing import Dict, Any
from conversation.models import IntentType, IntentResult


class IntentProcessor:
    """
    Classifies intent of user turn text using linguistic heuristics, syntax analysis,
    and reference patterns.
    """

    QUESTION_INDICATORS = {
        "what", "why", "how", "when", "where", "who", "which", "is", "are", "can",
        "could", "would", "should", "do", "does", "did", "has", "have", "?"
    }

    COMMAND_INDICATORS = {
        "run", "start", "stop", "create", "delete", "open", "close", "build", "execute",
        "set", "update", "cancel", "clear", "reset", "show", "get", "fetch"
    }

    FOLLOW_UP_INDICATORS = {
        "that", "it", "same", "previous", "again", "continue", "and then", "more", "tell me more"
    }

    def classify_intent(self, text: str, has_resolved_references: bool = False) -> IntentResult:
        if not text or not text.strip():
            return IntentResult(
                intent=IntentType.QUESTION,
                confidence=0.5,
                reason="empty_input_default",
            )

        text_lower = text.strip().lower()
        words = re.findall(r"\b\w+\b", text_lower)

        # 1. Check for Follow-Up
        if has_resolved_references or any(re.search(r"\b" + re.escape(ind) + r"\b", text_lower) for ind in self.FOLLOW_UP_INDICATORS):
            return IntentResult(
                intent=IntentType.FOLLOW_UP,
                confidence=0.90,
                reason="resolved_reference_or_follow_up_keyword",
            )

        # 2. Check for Question
        if text.endswith("?") or (words and words[0] in self.QUESTION_INDICATORS):
            return IntentResult(
                intent=IntentType.QUESTION,
                confidence=0.92,
                reason="question_mark_or_wh_word",
            )

        # 3. Check for Command
        if words and words[0] in self.COMMAND_INDICATORS:
            return IntentResult(
                intent=IntentType.COMMAND,
                confidence=0.88,
                reason="imperative_command_verb",
            )

        # 4. Check for Clarification / Short Phrase
        if len(words) <= 3:
            return IntentResult(
                intent=IntentType.CLARIFICATION,
                confidence=0.80,
                reason="short_phrase_clarification",
            )

        # Default to Continuation
        return IntentResult(
            intent=IntentType.CONTINUATION,
            confidence=0.85,
            reason="dialogue_continuation",
        )
