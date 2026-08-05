import time
from typing import List, Dict, Any, Optional

from intelligence.vision.models import VisionRequest, VisionImageItem, VisionResult
from intelligence.vision.vision_service import vision_service
from intelligence.vision.ocr.ocr_service import ocr_service
from intelligence.vision.ocr.models import OCRRequest
from intelligence.vision.multi_image.multi_image_service import multi_image_service
from intelligence.vision.camera.camera_service import camera_vision_service
from intelligence.vision.camera.session_manager import session_manager

from intelligence.vision.fusion.models import (
    CapabilityType,
    MultimodalFusionResponse,
    ClarificationRequest,
    RecoveryPrompt
)
from intelligence.vision.fusion.context_builder import context_builder
from intelligence.vision.fusion.pronoun_resolver import pronoun_resolver
from intelligence.vision.fusion.capability_router import capability_router
from intelligence.vision.fusion.clarification_engine import clarification_engine
from intelligence.vision.fusion.confidence_recovery import confidence_recovery_evaluator
from intelligence.vision.fusion.conflict_resolver import conflict_resolver
from tools.telemetry import log_structured, backend_log

class MultimodalFusionService:
    """
    Multimodal Fusion Service (V8).
    Unified multimodal conversation engine orchestrating:
    Context Builder -> Pronoun Resolver -> Clarification Check -> Multi-Signal Capability Router
                    -> Subsystem Execution (V1–V7) -> Conflict Resolver -> Confidence/Recovery Check.
    Reuses V1–V7 capabilities transparently without exposing implementation details to the user.
    """

    async def process_multimodal_request(
        self,
        prompt: Optional[str],
        image_items: List[VisionImageItem],
        session_id: Optional[str] = None,
        conversation_context: Optional[List[Dict[str, str]]] = None
    ) -> MultimodalFusionResponse:
        # 1. Retrieve or create temporary ephemeral multimodal context
        ctx = context_builder.get_or_create_context(session_id)
        if conversation_context:
            for turn in conversation_context:
                ctx.conversation_context.append(turn)

        # Check camera session active status
        camera_sess = session_manager.get_session(session_id) if session_id else None
        camera_focus = camera_sess.active_focus if camera_sess else None

        # 2. Cross-modal Pronoun Resolution
        pronoun_res = pronoun_resolver.resolve_pronouns(
            prompt=prompt or "",
            context=ctx,
            camera_focus=camera_focus
        )

        # 3. Clarification Engine Evaluation (Never guess if ambiguous!)
        clarification_req = clarification_engine.evaluate_clarification(
            pronoun_result=pronoun_res,
            prompt=prompt or "",
            context=ctx
        )

        if clarification_req.is_ambiguous:
            log_structured(backend_log, "INFO", f"[MultimodalFusionService] Ambiguity detected. Prompting for clarification...")
            return MultimodalFusionResponse(
                text=clarification_req.question or "Could you please clarify which object you are referring to?",
                capability_used=CapabilityType.VISION,
                pronoun_resolved=False,
                resolved_query=prompt or "",
                clarification=clarification_req,
                confidence_score=0.5,
                metadata={"ambiguity": True}
            )

        # 4. Multi-Signal Automatic Capability Router
        attachment_meta = [{"filename": img.filename, "size": img.size} for img in image_items]
        cap_res = capability_router.route_capability(
            prompt=pronoun_res.resolved_text,
            image_count=len(image_items),
            context=ctx,
            has_active_camera_session=bool(camera_sess),
            attachment_metadata=attachment_meta
        )

        log_structured(backend_log, "INFO", f"[MultimodalFusionService] Selected capability '{cap_res.selected_capability.value}': {cap_res.reason}")

        # Extract image bytes for recovery check
        raw_image_bytes = [img.data for img in image_items]
        if camera_sess and camera_sess.keyframes and not raw_image_bytes:
            raw_image_bytes = [camera_sess.keyframes[-1].data]

        # 5. Execute capability via V1–V7 subsystems
        selected_cap = cap_res.selected_capability
        result_text = ""
        visual_summary = ""
        task_type_used = selected_cap.value
        cap_metadata = {}

        if selected_cap == CapabilityType.CAMERA and camera_sess:
            frame_data = image_items[0].data if image_items else (camera_sess.keyframes[-1].data if camera_sess.keyframes else b"")
            cam_res = await camera_vision_service.process_camera_frame(
                session_id=session_id or camera_sess.session_id,
                frame_bytes=frame_data,
                user_prompt=pronoun_res.resolved_text
            )
            result_text = cam_res.text
            visual_summary = cam_res.visual_summary or ""
            task_type_used = cam_res.task_type
            cap_metadata = cam_res.metadata

        elif selected_cap == CapabilityType.OCR:
            ocr_req = OCRRequest(images=image_items)
            ocr_res = await ocr_service.extract(ocr_req)
            result_text = f"Extracted Text:\n{ocr_res.text}" if ocr_res.has_text else "No readable text detected."
            visual_summary = "OCR Extraction"
            task_type_used = "TEXT_EXTRACTION"
            cap_metadata = ocr_res.metadata
            context_builder.update_context(session_id, ocr_data={"text": ocr_res.text, "has_text": ocr_res.has_text})

        elif selected_cap == CapabilityType.MULTI_IMAGE:
            multi_req = VisionRequest(
                prompt=pronoun_res.resolved_text,
                images=image_items if len(image_items) >= 2 else (camera_sess.get_recent_keyframe_items() if camera_sess else image_items),
                conversation_context=ctx.conversation_context
            )
            multi_res = await multi_image_service.analyze_multi_images(multi_req)
            result_text = multi_res.text
            visual_summary = multi_res.visual_summary
            task_type_used = multi_res.task_type
            cap_metadata = multi_res.metadata
            context_builder.update_context(session_id, comparison_data={"text": multi_res.text, "summary": visual_summary})

        else: # VISION or SCREENSHOT
            v_req = VisionRequest(
                prompt=pronoun_res.resolved_text,
                images=image_items,
                conversation_context=ctx.conversation_context
            )
            v_res = await vision_service.analyze_images(v_req)
            result_text = v_res.text
            visual_summary = v_res.visual_summary
            task_type_used = v_res.task_type
            cap_metadata = v_res.metadata
            if selected_cap == CapabilityType.SCREENSHOT:
                context_builder.update_context(session_id, screenshot_data={"text": v_res.text, "summary": visual_summary})

        # 6. Reconcile subsystem outputs (Conflict Resolution)
        reconciled_text = conflict_resolver.reconcile_outputs(
            raw_text=result_text,
            capability=selected_cap.value,
            context=ctx,
            resolved_pronoun_target=pronoun_res.target_object
        )

        # 7. Confidence & Recovery Prompt Evaluator
        recovery_prompt = confidence_recovery_evaluator.evaluate(
            images_data=raw_image_bytes,
            analysis_text=reconciled_text
        )

        final_text = reconciled_text

        # Update context turn
        if prompt:
            context_builder.update_context(
                session_id=session_id,
                active_scene=visual_summary,
                explanation=final_text,
                turn={"user": prompt, "assistant": final_text}
            )

        merged_metadata = {
            "task_type": task_type_used,
            "visual_summary": visual_summary,
            "target_object": pronoun_res.target_object
        }
        if cap_metadata:
            merged_metadata.update(cap_metadata)

        return MultimodalFusionResponse(
            text=final_text,
            capability_used=selected_cap,
            pronoun_resolved=bool(pronoun_res.pronouns_found and not pronoun_res.is_ambiguous),
            resolved_query=pronoun_res.resolved_text,
            clarification=clarification_req,
            recovery_suggestion=recovery_prompt if recovery_prompt.needed else None,
            confidence_score=cap_res.confidence_score,
            metadata=merged_metadata
        )

# Singleton Instance
multimodal_fusion_service = MultimodalFusionService()
