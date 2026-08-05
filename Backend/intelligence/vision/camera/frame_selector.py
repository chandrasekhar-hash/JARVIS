import re
from typing import Optional
from intelligence.vision.camera.models import SceneChangeResult

_OCR_KEYWORDS = r"\b(read|extract|text|label|receipt|error|code|message|heading|invoice|words)\b"
_FOCUS_KEYWORDS = r"\b(look at|focus on|the|this|that|here|check the|show me)\b"

class FrameSelector:
    """
    Smart Frame Selector (V7).
    Determines whether a camera frame should be sent to Vision Intelligence
    based on 5 event triggers:
    1. Explicit user prompt / query
    2. Significant scene change
    3. Motion settled after camera movement
    4. Focus target update
    5. OCR extraction request
    """

    def should_process_frame(
        self,
        scene_result: SceneChangeResult,
        user_prompt: Optional[str] = None,
        has_active_focus: bool = False
    ) -> tuple[bool, str]:
        clean_prompt = (user_prompt or "").strip().lower()

        # Trigger 1: Explicit user prompt
        if clean_prompt:
            if re.search(_OCR_KEYWORDS, clean_prompt):
                return True, "Trigger: User OCR extraction request"
            if re.search(_FOCUS_KEYWORDS, clean_prompt):
                return True, "Trigger: User focus change request"
            return True, f"Trigger: Explicit user query ('{clean_prompt[:30]}...')"

        # Trigger 2 & 3: Significant scene change or motion settled
        if scene_result.should_analyze:
            return True, f"Trigger: Scene update ({scene_result.reason})"

        # Static scene & no prompt -> Skip frame to save API calls
        return False, "Skipped: Stable scene with no user query"

# Singleton Instance
frame_selector = FrameSelector()
