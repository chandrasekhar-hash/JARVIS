from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request

from intelligence.vision.models import VisionImageItem
from intelligence.vision.ocr.models import OCRRequest
from intelligence.vision.ocr.ocr_service import ocr_service, MAX_IMAGES_PER_REQUEST, MAX_IMAGE_SIZE_BYTES
from tools.telemetry import log_structured, backend_log

router = APIRouter(prefix="/api/vision", tags=["OCR Intelligence"])

@router.post("/ocr")
async def extract_ocr_text(
    request: Request,
    language_hint: Optional[str] = Form(None),
    preserve_layout: bool = Form(True),
    images: List[UploadFile] = File(...)
):
    """
    Dedicated OCR Text Extraction Endpoint (V4).
    Accepts multipart/form-data with images and optional language hint.
    Returns high-fidelity extracted text, per-image breakdown, and no-text status.
    """
    if not images or len(images) == 0:
        raise HTTPException(status_code=400, detail="No images provided in OCR upload request.")

    if len(images) > MAX_IMAGES_PER_REQUEST:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_IMAGES_PER_REQUEST} images allowed per request.")

    image_items = []
    for file in images:
        filename = file.filename or "uploaded_ocr.png"
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

    ocr_req = OCRRequest(
        images=image_items,
        language_hint=language_hint,
        preserve_layout=preserve_layout
    )

    try:
        result = await ocr_service.extract(ocr_req)
        return {
            "status": "success",
            "text": result.text,
            "has_text": result.has_text,
            "image_count": result.image_count,
            "images": [img.model_dump() for img in result.images],
            "provider": result.provider,
            "model": result.model,
            "metadata": result.metadata
        }
    except ValueError as val_err:
        err_msg = str(val_err)
        if "exceeds maximum allowed limit" in err_msg:
            raise HTTPException(status_code=413, detail=err_msg)
        raise HTTPException(status_code=400, detail=err_msg)
    except Exception as exc:
        log_structured(backend_log, "ERROR", f"[OCR API] Extraction error: {str(exc)}")
        raise HTTPException(status_code=500, detail="OCR Intelligence service encountered an error processing your request.")
