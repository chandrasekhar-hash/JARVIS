from abc import ABC, abstractmethod
from intelligence.vision.ocr.models import OCRRequest, OCRResult

class BaseOCRProvider(ABC):
    """
    Abstract Base Class for OCR Engine Providers.
    """

    @abstractmethod
    async def extract(self, request: OCRRequest) -> OCRResult:
        """
        Extracts textual content from images provided in request.
        Must return an OCRResult with per-image breakdowns and fidelity-oriented text.
        """
        pass
