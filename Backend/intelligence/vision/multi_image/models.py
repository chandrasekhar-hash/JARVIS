from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class RelationshipTag(str, Enum):
    SAME = "same"
    DIFFERENT = "different"
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    MOVED = "moved"
    REORDERED = "reordered"
    HIGHLIGHTED = "highlighted"
    UNCHANGED = "unchanged"
    UNKNOWN = "unknown"

class MultiImageTask(str, Enum):
    DIFFERENCE_DETECTION = "DIFFERENCE_DETECTION"
    BEFORE_AFTER = "BEFORE_AFTER"
    PROGRESS_TRACKING = "PROGRESS_TRACKING"
    UI_COMPARISON = "UI_COMPARISON"
    SCREENSHOT_COMPARISON = "SCREENSHOT_COMPARISON"
    DOCUMENT_COMPARISON = "DOCUMENT_COMPARISON"
    CHART_COMPARISON = "CHART_COMPARISON"
    DIAGRAM_COMPARISON = "DIAGRAM_COMPARISON"
    CODE_COMPARISON = "CODE_COMPARISON"
    TIMELINE_REASONING = "TIMELINE_REASONING"
    RANKING = "RANKING"
    BEST_CHOICE = "BEST_CHOICE"
    CONSISTENCY_CHECK = "CONSISTENCY_CHECK"
    DUPLICATE_DETECTION = "DUPLICATE_DETECTION"
    CROSS_CORRELATION = "CROSS_CORRELATION"
    GENERAL_COMPARISON = "GENERAL_COMPARISON"

class ImageRelationshipItem(BaseModel):
    pair: str
    relationship: RelationshipTag
    details: str
    confidence: Optional[float] = 1.0

class StructuredComparison(BaseModel):
    summary: str = ""
    additions: List[str] = Field(default_factory=list)
    removals: List[str] = Field(default_factory=list)
    modifications: List[str] = Field(default_factory=list)
    reorderings: List[str] = Field(default_factory=list)
    ranking: List[Dict[str, Any]] = Field(default_factory=list)
    ranking_criteria: Optional[str] = None
    inconsistencies: List[str] = Field(default_factory=list)
    duplicates: List[str] = Field(default_factory=list)
    chronology_inferred: bool = False
    chronology_explanation: Optional[str] = None
    best_choice: Optional[str] = None

class MultiImageContext(BaseModel):
    image_count: int
    image_names: List[str]
    is_exact_duplicates: bool = False
    duplicate_pairs: List[List[int]] = Field(default_factory=list)
    requires_ocr: bool = False
    ocr_text_by_image: Dict[int, str] = Field(default_factory=dict)
    task: MultiImageTask = MultiImageTask.GENERAL_COMPARISON
    user_intent: str = ""
    temporal_indicated_by_user: bool = False

class MultiImageResult(BaseModel):
    text: str
    task_type: str
    image_count: int
    relationships: List[ImageRelationshipItem] = Field(default_factory=list)
    structured_comparison: StructuredComparison
    ocr_used: bool = False
    visual_summary: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
