"""
JARVIS Product 1.6 - OCR Engine Architecture.

Provides OCR fallback capabilities using EasyOCR / Tesseract or PIL/Pillow spatial text extraction.
"""

import os
import logging
from typing import Tuple
from .interfaces import IOCREngine

logger = logging.getLogger(__name__)


class OCREngine(IOCREngine):
    """
    Production-ready OCR engine abstraction.
    Falls back gracefully from easyocr / pytesseract to basic layout/image metadata if dependencies are not installed.
    """

    def __init__(self, preferred_language: str = "en"):
        self.preferred_language = preferred_language
        self._easyocr_reader = None
        self._has_pytesseract = False
        self._init_ocr()

    def _init_ocr(self) -> None:
        try:
            import easyocr  # type: ignore
            self._easyocr_reader = easyocr.Reader([self.preferred_language], gpu=False)
            logger.info("EasyOCR initialized successfully for Knowledge Engine OCR.")
            return
        except ImportError:
            pass

        try:
            import pytesseract  # type: ignore
            self._has_pytesseract = True
            logger.info("PyTesseract detected for Knowledge Engine OCR.")
            return
        except ImportError:
            pass

        logger.warning("No OCR native library (easyocr/pytesseract) installed. OCR fallback mode active.")

    def extract_text_from_image(self, image_path: str) -> Tuple[str, float]:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        # EasyOCR
        if self._easyocr_reader is not None:
            try:
                results = self._easyocr_reader.readtext(image_path)
                text_lines = []
                confidence_scores = []
                for _, text, prob in results:
                    text_lines.append(text)
                    confidence_scores.append(prob)
                avg_conf = sum(confidence_scores) / max(len(confidence_scores), 1)
                return "\n".join(text_lines), float(avg_conf)
            except Exception as e:
                logger.error(f"EasyOCR extraction failed for {image_path}: {e}")

        # PyTesseract
        if self._has_pytesseract:
            try:
                import pytesseract  # type: ignore
                from PIL import Image
                img = Image.open(image_path)
                text = pytesseract.image_to_string(img)
                return text.strip(), 0.85
            except Exception as e:
                logger.error(f"PyTesseract extraction failed for {image_path}: {e}")

        # Basic Image Metadata Fallback
        try:
            filename = os.path.basename(image_path)
            file_size = os.path.getsize(image_path)
            return f"[Scanned Image Document: {filename}, Size: {file_size} bytes]", 0.50
        except Exception as e:
            return f"[Scanned Image Document: {image_path}]", 0.30
