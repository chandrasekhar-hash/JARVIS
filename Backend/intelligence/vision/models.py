from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class VisionImageItem(BaseModel):
    filename: str
    content_type: str
    data: bytes = Field(exclude=True) # Exclude raw bytes from dict/JSON dumps for security & performance
    size: int

class VisionRequest(BaseModel):
    prompt: Optional[str] = None
    images: List[VisionImageItem]
    conversation_context: Optional[List[Dict[str, str]]] = None
    task_type: Optional[str] = None

class VisionResult(BaseModel):
    text: str
    provider: str = "Gemini"
    model: str
    image_count: int
    task_type: str = "GENERAL_DESCRIPTION"
    visual_summary: Optional[str] = None
    uncertainty: bool = False
    usage: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
