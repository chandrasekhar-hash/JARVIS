"""
JARVIS Product 1.6 - Image OCR Parser.
Handles scanned images (PNG, JPG, WEBP, TIFF) via OCREngine.
"""

import os
import logging
from typing import Tuple, Dict, Any, Optional
from .base import BaseParser
from ..ocr import OCREngine

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}


class ImageOCRParser(BaseParser):
    def __init__(self, ocr_engine: Optional[OCREngine] = None):
        super().__init__("ImageOCRParser")
        self.ocr_engine = ocr_engine or OCREngine()

    def can_parse(self, source: str, mime_type: Optional[str] = None) -> bool:
        if mime_type and mime_type.lower().startswith("image/"):
            return True
        ext = os.path.splitext(source)[1].lower()
        return ext in IMAGE_EXTENSIONS

    def parse(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Image file not found: {file_path}")

        extracted_text, confidence = self.ocr_engine.extract_text_from_image(file_path)

        metadata = {
            "image_filename": os.path.basename(file_path),
            "ocr_confidence": confidence,
            "parsed_by": "ImageOCRParser",
        }

        return extracted_text, metadata
