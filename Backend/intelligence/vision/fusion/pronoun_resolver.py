import re
from typing import List, Optional
from intelligence.vision.fusion.models import MultimodalContext, PronounResolutionResult

_PRONOUN_PATTERN = r"\b(this|that|here|there|it|these|those)\b"

class PronounResolver:
    """
    Cross-Modal Pronoun Resolver (V8).
    Resolves ambiguous demonstratives ('this', 'that', 'here', 'there', 'it', 'these', 'those')
    against active focus, camera session state, and conversation history.
    NEVER guesses if multiple valid interpretations exist — flags ambiguity for Clarification Engine.
    """

    def resolve_pronouns(
        self,
        prompt: str,
        context: MultimodalContext,
        camera_focus: Optional[str] = None
    ) -> PronounResolutionResult:
        if not prompt or not prompt.strip():
            return PronounResolutionResult(resolved_text="", pronouns_found=[])

        clean_prompt = prompt.strip()
        matches = re.findall(_PRONOUN_PATTERN, clean_prompt, re.IGNORECASE)
        pronouns_found = list(set(p.lower() for p in matches))

        if not pronouns_found:
            return PronounResolutionResult(
                resolved_text=clean_prompt,
                pronouns_found=[],
                is_ambiguous=False,
                confidence=1.0
            )

        # Collect candidate targets from multimodal context
        candidates: List[str] = []
        if camera_focus and camera_focus.strip():
            candidates.append(camera_focus.strip())
        if context.active_focus and context.active_focus.strip() and context.active_focus.strip() not in candidates:
            candidates.append(context.active_focus.strip())
        if context.latest_ocr and context.latest_ocr.get("text"):
            ocr_text = context.latest_ocr.get("text", "")[:30].strip()
            if ocr_text and ocr_text not in candidates:
                candidates.append(f"Label text '{ocr_text}'")

        # Scenario 1: Exactly 1 unambiguous target object available
        if len(candidates) == 1:
            target = candidates[0]
            resolved = re.sub(
                _PRONOUN_PATTERN,
                f"the {target}",
                clean_prompt,
                flags=re.IGNORECASE
            )
            return PronounResolutionResult(
                resolved_text=resolved,
                pronouns_found=pronouns_found,
                target_object=target,
                is_ambiguous=False,
                confidence=0.95
            )

        # If explicit comparison phrase exists (e.g. 'with the', 'compared to', 'and the') or prompt has > 20 chars
        has_explicit_comparison = bool(re.search(r"\b(with the|compared to|and the|than the|versus|vs)\b", clean_prompt, re.IGNORECASE))
        if has_explicit_comparison:
            primary_target = candidates[0] if candidates else "primary object"
            resolved = re.sub(
                r"\b(this|these)\b",
                f"the current object",
                clean_prompt,
                flags=re.IGNORECASE
            )
            resolved = re.sub(
                r"\b(that|those)\b",
                f"the {primary_target}",
                resolved,
                flags=re.IGNORECASE
            )
            return PronounResolutionResult(
                resolved_text=resolved,
                pronouns_found=pronouns_found,
                target_object=primary_target,
                is_ambiguous=False,
                confidence=0.90
            )

        # Scenario 2: Multiple distinct candidates available & vague query -> AMBIGUOUS (Never guess!)
        if len(candidates) > 1:
            return PronounResolutionResult(
                resolved_text=clean_prompt,
                pronouns_found=pronouns_found,
                is_ambiguous=True,
                ambiguity_candidates=candidates[:3],
                confidence=0.5
            )

        # Scenario 3: No active focus or candidates found -> Retain original prompt
        return PronounResolutionResult(
            resolved_text=clean_prompt,
            pronouns_found=pronouns_found,
            is_ambiguous=False,
            confidence=0.8
        )

# Singleton Instance
pronoun_resolver = PronounResolver()
