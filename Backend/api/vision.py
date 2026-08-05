import json
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from pydantic import BaseModel

from intelligence.vision.models import VisionRequest, VisionImageItem
from intelligence.vision.vision_service import vision_service, MAX_IMAGES_PER_REQUEST, MAX_IMAGE_SIZE_BYTES
from tools.telemetry import log_structured, backend_log

router = APIRouter(prefix="/api/vision", tags=["Vision Intelligence"])

async def _parse_upload_files(images: List[UploadFile]) -> List[VisionImageItem]:
    if not images or len(images) == 0:
        raise HTTPException(status_code=400, detail="No images provided in upload request.")

    if len(images) > MAX_IMAGES_PER_REQUEST:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_IMAGES_PER_REQUEST} images allowed per request.")

    image_items = []
    for file in images:
        filename = file.filename or "uploaded_image.png"
        content_type = file.content_type or "image/png"
        
        try:
            data = await file.read()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to read file '{filename}': {str(e)}")

        if not data or len(data) == 0:
            raise HTTPException(status_code=400, detail=f"File '{filename}' is empty (0 bytes).")

        if len(data) > MAX_IMAGE_SIZE_BYTES:
            raise HTTPException(status_code=413, detail=f"Image '{filename}' exceeds maximum allowed size of 10 MB.")

        image_items.append(VisionImageItem(
            filename=filename,
            content_type=content_type,
            data=data,
            size=len(data)
        ))
    return image_items

@router.post("/analyze")
async def analyze_vision_images(
    request: Request,
    prompt: Optional[str] = Form(None),
    images: List[UploadFile] = File(...),
    conversation_context: Optional[str] = Form(None)
):
    """
    Multimodal Vision Analysis Endpoint (V3).
    Accepts multipart/form-data with images and optional prompt.
    Returns V3 task_type and bounded visual_summary for follow-up continuity.
    """
    image_items = await _parse_upload_files(images)

    # Parse optional conversation context JSON
    parsed_context = None
    if conversation_context:
        try:
            parsed_context = json.loads(conversation_context)
        except Exception:
            pass

    vision_req = VisionRequest(
        prompt=prompt,
        images=image_items,
        conversation_context=parsed_context
    )

    try:
        import time
        from intelligence.vision.fusion.fusion_service import multimodal_fusion_service
        req_sid = f"req_{int(time.time() * 1000)}"
        fusion_res = await multimodal_fusion_service.process_multimodal_request(
            prompt=prompt,
            image_items=image_items,
            session_id=req_sid,
            conversation_context=parsed_context
        )
        return {
            "status": "success",
            "text": fusion_res.text,
            "provider": "Gemini",
            "model": "gemini-2.5-flash",
            "image_count": len(image_items),
            "task_type": fusion_res.metadata.get("task_type", fusion_res.capability_used.value),
            "visual_summary": fusion_res.metadata.get("visual_summary", ""),
            "metadata": fusion_res.metadata
        }
    except ValueError as val_err:
        err_msg = str(val_err)
        if "exceeds maximum allowed limit" in err_msg:
            raise HTTPException(status_code=413, detail=err_msg)
        raise HTTPException(status_code=400, detail=err_msg)
    except Exception as exc:
        log_structured(backend_log, "ERROR", f"[Vision API] Vision analysis error: {str(exc)}")
        raise HTTPException(status_code=500, detail="Vision Intelligence service encountered an error processing your request.")

@router.post("/multi-image")
async def analyze_multi_images_endpoint(
    request: Request,
    prompt: Optional[str] = Form(None),
    images: List[UploadFile] = File(...),
    conversation_context: Optional[str] = Form(None)
):
    """
    Dedicated Multi-Image Intelligence Endpoint (V6).
    Accepts 2 to 5 image uploads and optional prompt.
    Returns structured cross-image relationships, domain comparison details, and visual summary.
    """
    if not images or len(images) < 2:
        raise HTTPException(status_code=400, detail="At least 2 images are required for multi-image analysis.")

    image_items = await _parse_upload_files(images)

    parsed_context = None
    if conversation_context:
        try:
            parsed_context = json.loads(conversation_context)
        except Exception:
            pass

    vision_req = VisionRequest(
        prompt=prompt,
        images=image_items,
        conversation_context=parsed_context
    )

    try:
        from intelligence.vision.multi_image.multi_image_service import multi_image_service
        result = await multi_image_service.analyze_multi_images(vision_req)
        return {
            "status": "success",
            "text": result.text,
            "provider": result.provider,
            "model": result.model,
            "image_count": result.image_count,
            "task_type": result.task_type,
            "visual_summary": result.visual_summary,
            "relationships": result.metadata.get("relationships", []),
            "structured_comparison": result.metadata.get("structured_comparison", {}),
            "metadata": result.metadata
        }
    except ValueError as val_err:
        err_msg = str(val_err)
        if "exceeds maximum allowed limit" in err_msg:
            raise HTTPException(status_code=413, detail=err_msg)
        raise HTTPException(status_code=400, detail=err_msg)
    except Exception as exc:
        log_structured(backend_log, "ERROR", f"[Vision API] Multi-image analysis error: {str(exc)}")
        raise HTTPException(status_code=500, detail="Multi-Image Intelligence service encountered an error processing your request.")

# ---------------------------------------------------------------------------
# Camera Vision Session Endpoints (V7)
# ---------------------------------------------------------------------------

@router.post("/camera/session/start")
async def start_camera_session(session_id: Optional[str] = Form(None)):
    """
    Initializes a new Camera Vision Session (V7).
    Returns session_id and active status.
    """
    import time
    from intelligence.vision.camera.session_manager import session_manager
    sid = session_id or f"session_{int(time.time())}"
    session = session_manager.get_or_create_session(sid)
    return {
        "status": "success",
        "session_id": session.session_id,
        "active_focus": session.active_focus,
        "status_text": "Camera Vision Session initialized"
    }

@router.post("/camera/session/frame")
async def process_camera_frame_endpoint(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    prompt: Optional[str] = Form(None)
):
    """
    Processes an incoming camera frame for an active Vision Session (V7).
    Evaluates lightweight scene change detection, frame selection, and context building.
    """
    if not file:
        raise HTTPException(status_code=400, detail="No camera frame file uploaded.")

    try:
        frame_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read camera frame bytes: {str(e)}")

    if not frame_bytes or len(frame_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded camera frame is empty (0 bytes).")

    if len(frame_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Camera frame exceeds maximum size limit of 10 MB.")

    try:
        from intelligence.vision.camera.camera_service import camera_vision_service
        result = await camera_vision_service.process_camera_frame(
            session_id=session_id,
            frame_bytes=frame_bytes,
            user_prompt=prompt
        )
        return {
            "status": "success",
            "session_id": result.session_id,
            "text": result.text,
            "scene_changed": result.scene_changed,
            "active_focus": result.active_focus,
            "task_type": result.task_type,
            "visual_summary": result.visual_summary,
            "metadata": result.metadata
        }
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        log_structured(backend_log, "ERROR", f"[Camera API] Camera frame processing error: {str(exc)}")
        raise HTTPException(status_code=500, detail="Camera Vision Intelligence encountered an error processing the frame.")

@router.get("/camera/session/status")
async def get_camera_session_status(session_id: str):
    """
    Queries current status, active focus, and keyframe count for a Camera Vision Session.
    """
    from intelligence.vision.camera.session_manager import session_manager
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Vision session '{session_id}' not found or expired.")

    return {
        "status": "success",
        "session_id": session.session_id,
        "session_status": session.status.value,
        "active_focus": session.active_focus,
        "keyframe_count": len(session.keyframes),
        "scene_summary": session.scene_summary
    }

@router.post("/camera/session/end")
async def end_camera_session(session_id: str = Form(...)):
    """
    Terminates a Camera Vision Session and purges all ephemeral memory.
    """
    from intelligence.vision.camera.session_manager import session_manager
    session_manager.purge_session(session_id)
    return {
        "status": "success",
        "session_id": session_id,
        "message": "Vision Session terminated and memory purged cleanly."
    }


