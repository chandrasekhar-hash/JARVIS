import io
from typing import List, Dict, Any, Optional
from PIL import Image, ImageOps

from intelligence.vision.models import VisionImageItem
from intelligence.vision.ocr.models import OCRRequest, OCRResult
from intelligence.vision.ocr.providers.gemini_ocr import GeminiOCRProvider
from tools.telemetry import log_structured, backend_log

# Shared limits
MAX_IMAGES_PER_REQUEST = 5
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_PIL_FORMATS = {"JPEG", "PNG", "WEBP"}

Image.MAX_IMAGE_PIXELS = 80_000_000

class OCRService:
    """
    OCR Service Facade (V4).
    Validates images, handles conservative EXIF orientation correction,
    and delegates to active OCRProvider.
    """

    def __init__(self):
        self.provider = GeminiOCRProvider()

    def process_exif_orientation(self, data: bytes) -> bytes:
        """
        Conservative preprocessing: applies EXIF orientation transpose if metadata exists.
        Does NOT alter colors, apply thresholding, or modify contrast.
        """
        try:
            with Image.open(io.BytesIO(data)) as img:
                fmt = img.format or "PNG"
                transposed = ImageOps.exif_transpose(img)
                buf = io.BytesIO()
                transposed.save(buf, format=fmt)
                return buf.getvalue()
        except Exception:
            return data

    def validate_image_bytes(self, data: bytes, filename: str) -> str:
        """
        Performs thorough server-side validation on raw image bytes.
        """
        if not data or len(data) == 0:
            raise ValueError(f"Image '{filename}' is empty (0 bytes).")

        if len(data) > MAX_IMAGE_SIZE_BYTES:
            size_mb = len(data) / (1024 * 1024)
            raise ValueError(f"Image '{filename}' ({size_mb:.1f} MB) exceeds maximum allowed limit of 10 MB.")

        try:
            with Image.open(io.BytesIO(data)) as img:
                img.verify()
                fmt = img.format.upper() if img.format else ""
                if fmt not in ALLOWED_PIL_FORMATS:
                    raise ValueError(f"Image '{filename}' format '{fmt}' is not supported. Allowed formats: JPEG, PNG, WEBP.")
                mime_map = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
                return mime_map.get(fmt, "image/jpeg")
        except Exception as e:
            if isinstance(e, ValueError):
                raise e
            raise ValueError(f"File '{filename}' is corrupted or is not a valid image.")

    async def extract(self, request: OCRRequest) -> OCRResult:
        """
        Validates images, applies EXIF transpose, and routes to active OCR provider.
        """
        if not request.images or len(request.images) == 0:
            raise ValueError("No images provided in OCR request.")

        if len(request.images) > MAX_IMAGES_PER_REQUEST:
            raise ValueError(f"Maximum {MAX_IMAGES_PER_REQUEST} images allowed per OCR request.")

        processed_items = []
        for item in request.images:
            mime = self.validate_image_bytes(item.data, item.filename)
            processed_bytes = self.process_exif_orientation(item.data)
            processed_items.append(VisionImageItem(
                filename=item.filename,
                content_type=mime,
                data=processed_bytes,
                size=len(processed_bytes)
            ))

        validated_req = OCRRequest(
            images=processed_items,
            language_hint=request.language_hint,
            preserve_layout=request.preserve_layout,
            task=request.task
        )

        log_structured(backend_log, "INFO", f"[OCRService] Extracting text from {len(processed_items)} image(s)...")

        result = await self.provider.extract(validated_req)
        return result

# Singleton Instance
ocr_service = OCRService()
