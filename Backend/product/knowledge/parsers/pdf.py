"""
JARVIS Product 1.6 - PDF Parser.
Supports pypdf / pymupdf (fitz) / pdfplumber fallback.
"""

import os
import logging
from typing import Tuple, Dict, Any, Optional
from .base import BaseParser

logger = logging.getLogger(__name__)


class PDFParser(BaseParser):
    def __init__(self):
        super().__init__("PDFParser")

    def can_parse(self, source: str, mime_type: Optional[str] = None) -> bool:
        if mime_type and mime_type.lower() == "application/pdf":
            return True
        return source.lower().endswith(".pdf")

    def parse(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        extracted_text = []
        metadata = {"total_pages": 0, "extracted_with": "none"}

        # Attempt 1: fitz (PyMuPDF)
        try:
            import fitz  # type: ignore
            doc = fitz.open(file_path)
            metadata["total_pages"] = len(doc)
            metadata["extracted_with"] = "PyMuPDF"
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text and text.strip():
                    extracted_text.append(f"--- [Page {page_num + 1}] ---\n{text.strip()}")
            doc.close()
            if extracted_text:
                return "\n\n".join(extracted_text), metadata
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"PyMuPDF failed for {file_path}: {e}")

        # Attempt 2: pypdf
        try:
            import pypdf  # type: ignore
            reader = pypdf.PdfReader(file_path)
            metadata["total_pages"] = len(reader.pages)
            metadata["extracted_with"] = "pypdf"
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    extracted_text.append(f"--- [Page {i + 1}] ---\n{text.strip()}")
            if extracted_text:
                return "\n\n".join(extracted_text), metadata
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"pypdf failed for {file_path}: {e}")

        # Fallback: Plain binary text extraction
        with open(file_path, "rb") as f:
            raw_bytes = f.read()
        cleaned = "".join([chr(b) if 32 <= b <= 126 or b in (10, 13, 9) else " " for b in raw_bytes])
        return cleaned[:5000], {"total_pages": 1, "extracted_with": "binary_fallback"}
