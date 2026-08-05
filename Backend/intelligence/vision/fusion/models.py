from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class CapabilityType(str, Enum):
    VISION = "VISION"
    OCR = "OCR"
    SCREENSHOT = "SCREENSHOT"
    MULTI_IMAGE = "MULTI_IMAGE"
    CAMERA = "CAMERA"

class MultimodalContext(BaseModel):
    """
    Temporary Ephemeral Multimodal Context (V8).
    Maintains context across recent speech, camera sessions, OCR, multi-image, and screenshots.
    No permanent storage.
    """
    session_id: Optional[str] = None
    active_focus: Optional[str] = None
    active_scene: Optional[str] = None
    latest_ocr: Optional[Dict[str, Any]] = None
    latest_comparison: Optional[Dict[str, Any]] = None
    latest_screenshot: Optional[Dict[str, Any]] = None
    recent_explanations: List[str] = Field(default_factory=list)
    conversation_context: List[Dict[str, str]] = Field(default_factory=list)
    last_updated_at: float = 0.0

class PronounResolutionResult(BaseModel):
    resolved_text: str
    pronouns_found: List[str] = Field(default_factory=list)
    target_object: Optional[str] = None
    is_ambiguous: bool = False
    ambiguity_candidates: List[str] = Field(default_factory=list)
    confidence: float = 1.0

class AutoCapabilityResult(BaseModel):
    selected_capability: CapabilityType
    reason: str
    confidence_score: float = 1.0

class ClarificationRequest(BaseModel):
    is_ambiguous: bool = False
    question: Optional[str] = None
    options: List[str] = Field(default_factory=list)

class RecoveryPrompt(BaseModel):
    needed: bool = False
    suggestion: Optional[str] = None
    reason: Optional[str] = None

class MultimodalFusionResponse(BaseModel):
    """
    Unified Assistant Response (V8).
    Combines outputs from Vision, OCR, Camera, and MultiImage into a single coherent response.
    """
    text: str
    capability_used: CapabilityType
    pronoun_resolved: bool = False
    resolved_query: str
    clarification: Optional[ClarificationRequest] = None
    recovery_suggestion: Optional[RecoveryPrompt] = None
    confidence_score: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
