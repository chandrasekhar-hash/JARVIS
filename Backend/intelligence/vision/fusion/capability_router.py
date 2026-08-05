import re
from typing import List, Dict, Any, Optional
from intelligence.vision.fusion.models import CapabilityType, AutoCapabilityResult, MultimodalContext

_OCR_PATTERNS = r"\b(read|extract|label|receipt|invoice|words|heading)\b"
_SCREENSHOT_PATTERNS = r"\b(screenshot|terminal|vs code|vscode|ide|editor|browser|console|stack trace|traceback|dashboard|github|pr|code|error)\b"
_COMPARE_PATTERNS = r"\b(compare|changed|moved|what changed|difference|different|same|reordered|before|after)\b"

class AutomaticCapabilityRouter:
    """
    Multi-Signal Capability Router (V8).
    Automatically selects the optimal vision capability based on multi-signal analysis:
    - User prompt / speech
    - Active camera session
    - Active focus target
    - Image attachments (count, format, metadata)
    - Recent multimodal context (recent OCR, screenshots, comparisons)
    No frontend selection required.
    """

    def route_capability(
        self,
        prompt: Optional[str],
        image_count: int,
        context: MultimodalContext,
        has_active_camera_session: bool = False,
        attachment_metadata: Optional[List[Dict[str, Any]]] = None
    ) -> AutoCapabilityResult:
        clean_prompt = (prompt or "").strip().lower()

        # Signal 1: Multiple attached images -> MULTI_IMAGE
        if image_count >= 2:
            return AutoCapabilityResult(
                selected_capability=CapabilityType.MULTI_IMAGE,
                reason=f"Multi-signal: {image_count} attached images require multi-image cross reasoning.",
                confidence_score=0.98
            )

        # Signal 2: Active Camera Vision Session -> CAMERA
        if has_active_camera_session and image_count <= 1:
            if re.search(_OCR_PATTERNS, clean_prompt):
                return AutoCapabilityResult(
                    selected_capability=CapabilityType.OCR,
                    reason="Multi-signal: Active camera session + explicit text extraction request.",
                    confidence_score=0.95
                )
            if re.search(_COMPARE_PATTERNS, clean_prompt):
                return AutoCapabilityResult(
                    selected_capability=CapabilityType.MULTI_IMAGE,
                    reason="Multi-signal: Active camera session + temporal frame comparison request.",
                    confidence_score=0.95
                )
            return AutoCapabilityResult(
                selected_capability=CapabilityType.CAMERA,
                reason="Multi-signal: Active ephemeral camera session stream.",
                confidence_score=0.95
            )

        # Signal 3: Code / IDE / Terminal / Screen screenshot indicators -> SCREENSHOT
        filename_has_screenshot = False
        if attachment_metadata:
            for meta in attachment_metadata:
                fname = meta.get("filename", "").lower()
                if "screen" in fname or "shot" in fname or "capture" in fname:
                    filename_has_screenshot = True
                    break

        if filename_has_screenshot or re.search(_SCREENSHOT_PATTERNS, clean_prompt) or (context.session_id and context.session_id != "default_fusion_session" and context.latest_screenshot):
            return AutoCapabilityResult(
                selected_capability=CapabilityType.SCREENSHOT,
                reason="Multi-signal: Detected code, terminal, IDE, or screenshot metadata.",
                confidence_score=0.95
            )

        # Signal 4: Explicit text extraction or active OCR context -> OCR
        if re.search(_OCR_PATTERNS, clean_prompt):
            return AutoCapabilityResult(
                selected_capability=CapabilityType.OCR,
                reason="Multi-signal: Prompt requests text extraction or document reading.",
                confidence_score=0.92
            )

        # Signal 5: Comparison query on single frame with historical context -> MULTI_IMAGE
        if re.search(_COMPARE_PATTERNS, clean_prompt) and context.latest_comparison:
            return AutoCapabilityResult(
                selected_capability=CapabilityType.MULTI_IMAGE,
                reason="Multi-signal: Comparison requested with existing recent image context.",
                confidence_score=0.90
            )

        # Default Fallback: General Single-Image Vision Understanding
        return AutoCapabilityResult(
            selected_capability=CapabilityType.VISION,
            reason="Multi-signal: General single-image semantic vision analysis.",
            confidence_score=0.85
        )

# Singleton Instance
capability_router = AutomaticCapabilityRouter()
