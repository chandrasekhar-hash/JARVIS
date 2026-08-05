"""
Visual Task Classifier for JARVIS Vision Intelligence (V5).
Provides lightweight, local heuristic classification to serve as a task hint
for instruction construction and orchestrating visual vs OCR routing.

VisualTask describes the TYPE OF REASONING required, not the specific application.
Application-specific specialization is handled by ScreenTypeDetector.
"""

from enum import Enum
import re
from typing import List, Dict, Any, Optional

class VisualTask(str, Enum):
    # --- Core Reasoning Types ---
    GENERAL_DESCRIPTION = "GENERAL_DESCRIPTION"
    OBJECT_ANALYSIS = "OBJECT_ANALYSIS"
    SCENE_REASONING = "SCENE_REASONING"
    SPATIAL_REASONING = "SPATIAL_REASONING"
    UI_ANALYSIS = "UI_ANALYSIS"
    CHART_ANALYSIS = "CHART_ANALYSIS"
    DIAGRAM_ANALYSIS = "DIAGRAM_ANALYSIS"
    TEXT_HEAVY_IMAGE = "TEXT_HEAVY_IMAGE"
    IMAGE_COMPARISON = "IMAGE_COMPARISON"
    VISUAL_TROUBLESHOOTING = "VISUAL_TROUBLESHOOTING"
    TARGETED_QUESTION = "TARGETED_QUESTION"
    # --- OCR Routes (V4) ---
    TEXT_EXTRACTION = "TEXT_EXTRACTION"
    EXTRACTION_REASONING = "EXTRACTION_REASONING"
    # --- Screenshot Intelligence (V5) ---
    SCREENSHOT = "SCREENSHOT"

# --- Screenshot detection patterns ---
# Matches tool/app names or screen-type vocabulary that signals a software screenshot
_SCREENSHOT_APP_PATTERN = re.compile(
    r"\b("
    r"vscode|vs code|visual studio code|cursor editor|pycharm|intellij|android studio|"
    r"chrome|firefox|edge|safari|"
    r"devtools|dev tools|developer tools|console tab|network tab|elements tab|"
    r"powershell|command prompt|git bash|bash|zsh|fish shell|"
    r"github|gitlab|bitbucket|"
    r"docker|docker compose|docker desktop|"
    r"figma|canva|"
    r"notion|slack|discord|"
    r"supabase|firebase console|"
    r"react app|fastapi|next\.?js|vite|"
    r"admin panel|analytics dashboard|"
    r"iphone|ios settings|android settings|pixel|samsung"
    r")\b",
    re.IGNORECASE
)

_SCREENSHOT_GENERIC_PATTERN = re.compile(
    r"\b("
    r"screenshot|screen capture|"
    r"ide|editor|debugger|breakpoint|gutter|file tree|"
    r"terminal output|shell output|"
    r"browser tab|browser window|"
    r"os settings|system settings|control panel|"
    r"notification|status bar|taskbar|dock"
    r")\b",
    re.IGNORECASE
)

# --- Existing domain patterns ---
PATTERNS = {
    VisualTask.EXTRACTION_REASONING: r"\b(extract.*and (explain|tell|why|describe|fix|solve)|read.*and (explain|tell|why|fix)|copy.*and (explain|tell|why|fix)|get.*and (explain|tell|why))\b",
    VisualTask.TEXT_EXTRACTION: r"\b(extract|copy|transcribe|read all text|get (the )?(exact )?(text|error|code|message)|read receipt)\b",
    VisualTask.IMAGE_COMPARISON: r"\b(compare|difference|changed|versus|\bvs\b|between|before and after|after|diff)\b",
    VisualTask.UI_ANALYSIS: r"\b(ui|user interface|button|menu|screen|screenshot|dialog|tab|navbar|sidebar|form|checkbox|radio|dropdown|input|setting|select|selected|click)\b",
    VisualTask.VISUAL_TROUBLESHOOTING: r"\b(error|bug|issue|broken|fail|failed|failure|crash|crashed|why is|why isn't|why can't|disabled|wrong|404|500|exception|traceback|fix)\b",
    VisualTask.CHART_ANALYSIS: r"\b(chart|graph|plot|bar chart|line chart|pie chart|trend|axis|axes|legend|statistics|metric|data plot|dashboard|increase|decrease|highest|lowest)\b",
    VisualTask.DIAGRAM_ANALYSIS: r"\b(diagram|flowchart|architecture|flow|workflow|sequence|pipeline|process|network diagram|block diagram|component|nodes|arrows)\b",
    VisualTask.SPATIAL_REASONING: r"\b(left|right|above|below|top|bottom|foreground|background|beside|behind|in front of|under|over|next to|position|relative|closer)\b",
    VisualTask.TEXT_HEAVY_IMAGE: r"\b(text|read|document|poster|page|article|paragraph|sign|code snippet|receipt|invoice|ocr|transcript)\b",
    VisualTask.OBJECT_ANALYSIS: r"\b(object|item|thing|model|make|type|brand|material|texture|what is this)\b",
    VisualTask.SCENE_REASONING: r"\b(scene|happening|overview|context|environment|location|setting|place|activity|action|crowd|people doing)\b",
}

TARGETED_QUESTION_PATTERN = r"^(what|which|how|where|who|is|are|can|does|do|has|have|why)\b"


def classify_visual_task(
    prompt: Optional[str] = None,
    image_count: int = 1,
    conversation_context: Optional[List[Dict[str, Any]]] = None
) -> VisualTask:
    """
    Classifies the visual task into a VisualTask hint.
    Guarantees a sensible fallback for ambiguous prompts.

    V5: SCREENSHOT fires when prompt or context signals a software tool/app screenshot.
    All application-specific specialization is delegated to ScreenTypeDetector.
    """
    clean_prompt = (prompt or "").strip().lower()

    # Rule 1: Multi-image comparison
    if image_count > 1:
        if not clean_prompt or re.search(PATTERNS[VisualTask.IMAGE_COMPARISON], clean_prompt):
            return VisualTask.IMAGE_COMPARISON

    # Rule 2: Empty / generic ambiguous prompts
    if not clean_prompt or clean_prompt in {
        "explain this", "what is this?", "what do you think?",
        "describe", "look at this", "check this"
    }:
        return VisualTask.GENERAL_DESCRIPTION

    if clean_prompt in {"what's wrong?", "what is wrong?", "why isn't this working?", "why is this failing?"}:
        return VisualTask.VISUAL_TROUBLESHOOTING

    # Rule 3: OCR extraction intents — before screenshot and domain patterns
    if re.search(PATTERNS[VisualTask.EXTRACTION_REASONING], clean_prompt):
        return VisualTask.EXTRACTION_REASONING

    if re.search(PATTERNS[VisualTask.TEXT_EXTRACTION], clean_prompt):
        return VisualTask.TEXT_EXTRACTION

    # Rule 4: Screenshot intelligence — fires when a specific tool/app/screen-type is named
    if _SCREENSHOT_APP_PATTERN.search(clean_prompt) or _SCREENSHOT_GENERIC_PATTERN.search(clean_prompt):
        return VisualTask.SCREENSHOT

    # Rule 5: Domain-specific technical patterns
    for task in [
        VisualTask.UI_ANALYSIS,
        VisualTask.VISUAL_TROUBLESHOOTING,
        VisualTask.CHART_ANALYSIS,
        VisualTask.DIAGRAM_ANALYSIS,
        VisualTask.SPATIAL_REASONING,
        VisualTask.TEXT_HEAVY_IMAGE,
        VisualTask.IMAGE_COMPARISON,
    ]:
        if re.search(PATTERNS[task], clean_prompt):
            return task

    # Rule 6: Targeted question
    if re.search(TARGETED_QUESTION_PATTERN, clean_prompt):
        return VisualTask.TARGETED_QUESTION

    # Rule 7: Object / scene fallbacks
    for task in [VisualTask.OBJECT_ANALYSIS, VisualTask.SCENE_REASONING]:
        if re.search(PATTERNS[task], clean_prompt):
            return task

    return VisualTask.GENERAL_DESCRIPTION
