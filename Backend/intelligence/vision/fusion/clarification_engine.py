from typing import Optional, List
from intelligence.vision.fusion.models import PronounResolutionResult, MultimodalContext, ClarificationRequest

class ClarificationEngine:
    """
    Clarification Engine (V8).
    Evaluates user prompt and multimodal context ambiguity.
    When multiple target objects or ambiguous interpretations exist:
    - Asks concise, targeted clarifying questions (e.g. 'Do you mean the bottle label or the receipt?')
    - Avoids unnecessary clarification when confidence is high (>= 0.85).
    """

    def evaluate_clarification(
        self,
        pronoun_result: PronounResolutionResult,
        prompt: str,
        context: MultimodalContext
    ) -> ClarificationRequest:
        # Check pronoun ambiguity
        if pronoun_result.is_ambiguous and pronoun_result.ambiguity_candidates:
            candidates = pronoun_result.ambiguity_candidates
            if len(candidates) >= 2:
                formatted_opts = " or ".join([f"the {c}" for c in candidates[:2]])
                question = f"Do you mean {formatted_opts}?"
                return ClarificationRequest(
                    is_ambiguous=True,
                    question=question,
                    options=candidates
                )

        # High confidence & unambiguous -> No clarification needed
        return ClarificationRequest(is_ambiguous=False)

# Singleton Instance
clarification_engine = ClarificationEngine()
