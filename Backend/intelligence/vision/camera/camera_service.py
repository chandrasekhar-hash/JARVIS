import re
from typing import List, Dict, Any, Optional

from intelligence.vision.models import VisionRequest, VisionImageItem
from intelligence.vision.vision_service import vision_service
from intelligence.vision.ocr.ocr_service import ocr_service
from intelligence.vision.ocr.models import OCRRequest
from intelligence.vision.screenshot.screen_type_detector import screen_type_detector
from intelligence.vision.multi_image.multi_image_service import multi_image_service
from intelligence.vision.camera.models import CameraAnalysisResult, SceneChangeResult
from intelligence.vision.camera.scene_detector import scene_change_detector
from intelligence.vision.camera.frame_selector import frame_selector
from intelligence.vision.camera.session_manager import session_manager, VisionSession
from tools.telemetry import log_structured, backend_log

_COMPARE_PATTERNS = r"\b(changed|moved|what changed|what moved|same object|different|compare|before|earlier)\b"
_OCR_PATTERNS = r"\b(read|extract|text|label|receipt|error|code|message|heading|invoice|words|say)\b"

class CameraVisionService:
    """
    Camera Vision Service Facade (V7).
    Transforms JARVIS into a conversational camera assistant by orchestrating:
    Frame Selector -> Scene Change Detector -> VisionSessionManager
                  -> VisionService / OCRService / ScreenTypeDetector / MultiImageService.
    Reuses V1–V6 intelligence directly.
    """

    def _extract_focus_candidate(self, text: str) -> Optional[str]:
        """
        Lightweight focus object extractor from visual analysis text.
        """
        if not text:
            return None
        match = re.search(r"\b(showing|visible|contains|identified|is a|a|an)\s+([A-Za-z0-9_\-\s]{3,25})\b", text, re.IGNORECASE)
        if match:
            candidate = match.group(2).strip().title()
            if candidate.lower() not in {"this", "that", "there", "image", "picture", "frame", "something"}:
                return candidate
        return None

    async def process_camera_frame(
        self,
        session_id: str,
        frame_bytes: bytes,
        user_prompt: Optional[str] = None
    ) -> CameraAnalysisResult:
        if not frame_bytes or len(frame_bytes) == 0:
            raise ValueError("Camera frame bytes cannot be empty.")

        # 1. Retrieve or initialize active session
        session = session_manager.get_or_create_session(session_id)
        prev_kf = session.get_latest_keyframe()
        prev_bytes = prev_kf.data if prev_kf else None

        # 2. Evaluate lightweight scene change (< 5ms)
        scene_result = scene_change_detector.evaluate_change(frame_bytes, prev_bytes)

        # 3. Evaluate smart frame selector
        should_process, trigger_reason = frame_selector.should_process_frame(
            scene_result=scene_result,
            user_prompt=user_prompt,
            has_active_focus=bool(session.active_focus)
        )

        # Skip frame if static scene and no explicit prompt
        if not should_process and not user_prompt:
            log_structured(backend_log, "INFO", f"[CameraVisionService] Skipping static frame for session '{session_id}': {trigger_reason}")
            return CameraAnalysisResult(
                session_id=session_id,
                text=f"Scene stable. Active focus: {session.active_focus or 'General scene'}.",
                scene_changed=False,
                active_focus=session.active_focus,
                task_type="CAMERA_STABLE_SKIPPED",
                visual_summary=session.scene_summary or "Stable scene.",
                metadata={"trigger_reason": trigger_reason, "skipped": True}
            )

        # Store keyframe in session memory buffer
        kf = session.add_keyframe(frame_bytes)
        clean_prompt = (user_prompt or "").strip()

        # Construct contextual prompt incorporating active focus & conversational continuity
        context_prompt_parts = []
        if session.active_focus:
            context_prompt_parts.append(f"[CONVERSATIONAL FOCUS: The user and camera are currently focusing on '{session.active_focus}'. Resolve pronouns like 'this', 'here', 'that' to this focus object if applicable.]")

        if clean_prompt:
            context_prompt_parts.append(f"User Question: {clean_prompt}")
        else:
            context_prompt_parts.append("Describe the current scene and key objects concisely.")

        full_prompt = "\n".join(context_prompt_parts)

        # 4. ROUTE A: Multi-Image Temporal Query ("What changed?", "What moved?")
        if len(session.keyframes) >= 2 and re.search(_COMPARE_PATTERNS, clean_prompt.lower()):
            log_structured(backend_log, "INFO", f"[CameraVisionService] Routing to MultiImageService across {len(session.keyframes)} keyframes...")
            recent_items = session.get_recent_keyframe_items()
            multi_req = VisionRequest(
                prompt=clean_prompt or "What changed between recent camera frames?",
                images=recent_items,
                conversation_context=session.conversational_context
            )
            multi_res = await multi_image_service.analyze_multi_images(multi_req)

            session.add_turn("user", clean_prompt or "What changed?")
            session.add_turn("assistant", multi_res.text)

            return CameraAnalysisResult(
                session_id=session_id,
                text=multi_res.text,
                scene_changed=scene_result.should_analyze,
                active_focus=session.active_focus,
                task_type="CAMERA_MULTI_IMAGE",
                visual_summary=multi_res.visual_summary,
                metadata={"trigger_reason": trigger_reason, "keyframe_count": len(session.keyframes)}
            )

        # 5. ROUTE B: OCR Extraction Request
        if clean_prompt and re.search(_OCR_PATTERNS, clean_prompt.lower()):
            log_structured(backend_log, "INFO", f"[CameraVisionService] Routing frame to OCRService...")
            img_item = VisionImageItem(filename="camera_frame.jpg", content_type="image/jpeg", data=frame_bytes, size=len(frame_bytes))
            ocr_req = OCRRequest(images=[img_item])
            ocr_res = await ocr_service.extract(ocr_req)

            response_text = f"Extracted Text:\n{ocr_res.text}" if ocr_res.has_text else "No readable text detected in camera view."
            session.add_turn("user", clean_prompt)
            session.add_turn("assistant", response_text)

            return CameraAnalysisResult(
                session_id=session_id,
                text=response_text,
                scene_changed=scene_result.should_analyze,
                active_focus=session.active_focus,
                task_type="CAMERA_OCR",
                visual_summary="Camera view OCR extraction.",
                metadata={"has_text": ocr_res.has_text}
            )

        # 6. ROUTE C: Single Frame Visual Reasoning (VisionService + Screenshot detector)
        img_item = VisionImageItem(filename="camera_frame.jpg", content_type="image/jpeg", data=frame_bytes, size=len(frame_bytes))
        vision_req = VisionRequest(
            prompt=full_prompt,
            images=[img_item],
            conversation_context=session.conversational_context
        )

        log_structured(backend_log, "INFO", f"[CameraVisionService] Routing frame to VisionService...")
        result = await vision_service.analyze_images(vision_req)

        # Update active focus if detected
        new_focus = self._extract_focus_candidate(result.text)
        if new_focus:
            session.update_focus(new_focus)
        elif not session.active_focus and clean_prompt:
            session.update_focus(clean_prompt[:30])

        session.scene_summary = result.visual_summary
        if clean_prompt:
            session.add_turn("user", clean_prompt)
            session.add_turn("assistant", result.text)

        return CameraAnalysisResult(
            session_id=session_id,
            text=result.text,
            scene_changed=scene_result.should_analyze,
            active_focus=session.active_focus,
            task_type=result.task_type,
            visual_summary=result.visual_summary,
            metadata={"trigger_reason": trigger_reason, "scene_score": scene_result.score}
        )

# Singleton Instance
camera_vision_service = CameraVisionService()
