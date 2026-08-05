import time
from typing import Dict, Any, Optional, List
from intelligence.vision.fusion.models import MultimodalContext
from tools.telemetry import log_structured, backend_log

DEFAULT_CONTEXT_TIMEOUT_SECONDS = 300 # 5 minutes auto-timeout

class MultimodalContextBuilder:
    """
    Multimodal Context Builder (V8).
    Maintains temporary, ephemeral in-memory context across speech, camera sessions,
    active focus, recent OCR extractions, multi-image comparisons, and screenshots.
    Purges stale context automatically.
    """

    def __init__(self):
        self.contexts: Dict[str, MultimodalContext] = {}

    def get_or_create_context(self, session_id: Optional[str] = None) -> MultimodalContext:
        sid = session_id or "default_fusion_session"
        self.cleanup_expired_contexts()

        if sid not in self.contexts:
            log_structured(backend_log, "INFO", f"[MultimodalContextBuilder] Initializing new context for '{sid}'...")
            self.contexts[sid] = MultimodalContext(session_id=sid, last_updated_at=time.time())
        else:
            self.contexts[sid].last_updated_at = time.time()

        return self.contexts[sid]

    def update_context(
        self,
        session_id: Optional[str] = None,
        active_focus: Optional[str] = None,
        active_scene: Optional[str] = None,
        ocr_data: Optional[Dict[str, Any]] = None,
        comparison_data: Optional[Dict[str, Any]] = None,
        screenshot_data: Optional[Dict[str, Any]] = None,
        explanation: Optional[str] = None,
        turn: Optional[Dict[str, str]] = None
    ):
        ctx = self.get_or_create_context(session_id)
        ctx.last_updated_at = time.time()

        if active_focus:
            ctx.active_focus = active_focus.strip()
        if active_scene:
            ctx.active_scene = active_scene.strip()
        if ocr_data:
            ctx.latest_ocr = ocr_data
        if comparison_data:
            ctx.latest_comparison = comparison_data
        if screenshot_data:
            ctx.latest_screenshot = screenshot_data
        if explanation:
            ctx.recent_explanations.append(explanation[:500])
            if len(ctx.recent_explanations) > 5:
                ctx.recent_explanations.pop(0)
        if turn:
            ctx.conversation_context.append(turn)
            if len(ctx.conversation_context) > 10:
                ctx.conversation_context.pop(0)

    def purge_context(self, session_id: str):
        if session_id in self.contexts:
            log_structured(backend_log, "INFO", f"[MultimodalContextBuilder] Purging context for '{session_id}'...")
            del self.contexts[session_id]

    def cleanup_expired_contexts(self, timeout_seconds: int = DEFAULT_CONTEXT_TIMEOUT_SECONDS):
        now = time.time()
        expired = [
            sid for sid, ctx in self.contexts.items()
            if (now - ctx.last_updated_at) > timeout_seconds
        ]
        for sid in expired:
            log_structured(backend_log, "INFO", f"[MultimodalContextBuilder] Auto-purging expired context '{sid}'...")
            del self.contexts[sid]

# Singleton Instance
context_builder = MultimodalContextBuilder()
