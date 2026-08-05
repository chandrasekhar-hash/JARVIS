import re
from typing import Optional, Dict, Any
from intelligence.vision.fusion.models import MultimodalContext

class ConflictResolver:
    """
    Multimodal Output Conflict Resolver (V8).
    Reconciles potential conflicts between Vision, OCR, Camera, and MultiImage outputs
    into a single, coherent, natural assistant response.
    """

    def reconcile_outputs(
        self,
        raw_text: str,
        capability: str,
        context: MultimodalContext,
        resolved_pronoun_target: Optional[str] = None
    ) -> str:
        if not raw_text or not raw_text.strip():
            return "No visual analysis available."

        clean_text = raw_text.strip()

        # Reconcile OCR output with context
        if capability == "OCR":
            if "Extracted Text:" not in clean_text and not clean_text.startswith("No readable text"):
                clean_text = f"Extracted Text:\n{clean_text}"

        # Reconcile active focus consistency
        if resolved_pronoun_target and context.active_focus:
            if context.active_focus.lower() not in clean_text.lower():
                # Add context grounding if focus was missing from response
                pass

        # Clean redundant JSON tags or raw prompt markers if present
        clean_text = re.sub(r"\[CONVERSATIONAL FOCUS:.*?\]", "", clean_text, flags=re.DOTALL).strip()
        clean_text = re.sub(r"\n{3,}", "\n\n", clean_text)

        return clean_text

# Singleton Instance
conflict_resolver = ConflictResolver()
