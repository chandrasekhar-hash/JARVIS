from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from intelligence.vision.models import VisionImageItem

class OCRImageResult(BaseModel):
    index: int
    text: str
    has_text: bool
    detected_language: Optional[str] = None

class OCRRequest(BaseModel):
    images: List[VisionImageItem]
    language_hint: Optional[str] = None
    preserve_layout: bool = True
    task: Optional[str] = None

class OCRResult(BaseModel):
    text: str
    has_text: bool
    image_count: int
    images: List[OCRImageResult] = Field(default_factory=list)
    provider: str = "Gemini"
    model: str = "gemini-2.5-flash"
    metadata: Dict[str, Any] = Field(default_factory=dict)
