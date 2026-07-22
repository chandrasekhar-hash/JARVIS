from typing import List, Optional
from pydantic import BaseModel

class TextBoundingBox(BaseModel):
    x: int
    y: int
    width: int
    height: int
    center_x: int
    center_y: int

class TextElement(BaseModel):
    text_id: str
    text: str
    bbox: TextBoundingBox
    confidence: float
    line_number: int
    paragraph_id: int
    reading_order: int
    language: str = "en"

class OCRResult(BaseModel):
    frame_id: Optional[str] = None
    timestamp: float
    detected_elements: List[TextElement]
    full_text: str
    language: str = "en"
    processing_time_seconds: float
