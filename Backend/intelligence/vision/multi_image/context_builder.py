import hashlib
import re
from typing import List, Dict, Any, Optional

from intelligence.vision.models import VisionImageItem
from intelligence.vision.ocr.ocr_service import ocr_service
from intelligence.vision.ocr.models import OCRRequest
from intelligence.vision.multi_image.models import MultiImageContext, MultiImageTask
from tools.telemetry import log_structured, backend_log

_PATTERNS = {
    MultiImageTask.CONSISTENCY_CHECK: r"\b(consistent|inconsistent|inconsistencies|consistency|conflict|conflicting|contradict|contradiction|discrepancy|mismatch)\b",
    MultiImageTask.RANKING: r"\b(rank|ranking|best|choose|strongest|pick|top|select|which (one |is |design |logo |profile )?best)\b",
    MultiImageTask.DUPLICATE_DETECTION: r"\b(duplicate|identical|same image|repeated|copies)\b",
    MultiImageTask.CROSS_CORRELATION: r"\b(correlate|correlation|cross-reference|link|connect|relationship between)\b",
    MultiImageTask.CODE_COMPARISON: r"\b(code|function|import|variable|stack trace|traceback|syntax|git|repo|editor|vs code|pycharm|ide)\b",
    MultiImageTask.DOCUMENT_COMPARISON: r"\b(document|invoice|receipt|contract|page|paragraph|article|heading|table|report|pdf)\b",
    MultiImageTask.UI_COMPARISON: r"\b(ui|user interface|redesign|layout|button|navigation|spacing|theme|mockup|screen|component|form|dialog)\b",
    MultiImageTask.CHART_COMPARISON: r"\b(chart|graph|plot|kpi|metric|dashboard|trend|bar chart|line chart|pie chart)\b",
    MultiImageTask.DIAGRAM_COMPARISON: r"\b(diagram|flowchart|architecture|flow|workflow|network|sequence|block diagram)\b",
    MultiImageTask.BEFORE_AFTER: r"\b(before and after|before/after|before vs after|initial vs final)\b",
    MultiImageTask.PROGRESS_TRACKING: r"\b(progress|progression|evolution|timeline|over time|stages|phases|steps|history)\b",
    MultiImageTask.DIFFERENCE_DETECTION: r"\b(difference|compare|contrast|changed|what changed|diff|versus|\bvs\b|between)\b",
}

_TEMPORAL_PATTERNS = r"\b(chronolog|timeline|progress|over time|order|sequence|first|then|after|step|stage|evolution|history|before and after|before/after)\b"

class MultiImageContextBuilder:
    """
    MultiImage Context Builder (V6).
    Prepares context WITHOUT making visual inferences:
    - Image count & explicit image references (Image 1, Image 2...)
    - Byte/hash duplicate detection
    - Task & user intent classification
    - Temporal indication detection (chronology marked conditional on prompt)
    - OCR extraction context via OCRService when required (Document/Code comparison)
    """

    def detect_duplicates(self, images: List[VisionImageItem]) -> tuple[bool, List[List[int]]]:
        hashes = [hashlib.sha256(img.data).hexdigest() for img in images]
        duplicate_pairs = []
        for i in range(len(hashes)):
            for j in range(i + 1, len(hashes)):
                if hashes[i] == hashes[j]:
                    duplicate_pairs.append([i + 1, j + 1]) # 1-indexed image indices

        is_exact_duplicates = len(duplicate_pairs) > 0
        return is_exact_duplicates, duplicate_pairs

    def classify_task_intent(self, prompt: Optional[str], is_duplicates: bool) -> MultiImageTask:
        clean_prompt = (prompt or "").strip().lower()

        if is_duplicates and ("duplicate" in clean_prompt or "same" in clean_prompt or not clean_prompt):
            return MultiImageTask.DUPLICATE_DETECTION

        for task, pattern in _PATTERNS.items():
            if re.search(pattern, clean_prompt):
                return task

        return MultiImageTask.GENERAL_COMPARISON

    def check_temporal_indication(self, prompt: Optional[str]) -> bool:
        clean_prompt = (prompt or "").strip().lower()
        return bool(re.search(_TEMPORAL_PATTERNS, clean_prompt))

    def check_ocr_requirement(self, task: MultiImageTask, prompt: Optional[str]) -> bool:
        clean_prompt = (prompt or "").strip().lower()
        if task in (MultiImageTask.DOCUMENT_COMPARISON, MultiImageTask.CODE_COMPARISON):
            return True
        if "extract" in clean_prompt or "read text" in clean_prompt or "ocr" in clean_prompt:
            return True
        return False

    async def build_context(self, images: List[VisionImageItem], prompt: Optional[str] = None) -> MultiImageContext:
        image_count = len(images)
        image_names = [img.filename or f"Image_{idx}" for idx, img in enumerate(images, start=1)]

        is_duplicates, duplicate_pairs = self.detect_duplicates(images)
        task = self.classify_task_intent(prompt, is_duplicates)
        temporal_indicated = self.check_temporal_indication(prompt)
        requires_ocr = self.check_ocr_requirement(task, prompt)

        ocr_text_by_image: Dict[int, str] = {}

        # Reuse OCRService for document and code extractions
        if requires_ocr:
            try:
                log_structured(backend_log, "INFO", f"[MultiImageContextBuilder] Executing OCRService reuse for {image_count} images...")
                ocr_req = OCRRequest(images=images)
                ocr_res = await ocr_service.extract(ocr_req)
                for item in ocr_res.images:
                    ocr_text_by_image[item.index] = item.text
            except Exception as e:
                log_structured(backend_log, "WARNING", f"[MultiImageContextBuilder] OCRService extraction warning: {str(e)}")

        return MultiImageContext(
            image_count=image_count,
            image_names=image_names,
            is_exact_duplicates=is_duplicates,
            duplicate_pairs=duplicate_pairs,
            requires_ocr=requires_ocr,
            ocr_text_by_image=ocr_text_by_image,
            task=task,
            user_intent=prompt or "Compare these images and explain relationships.",
            temporal_indicated_by_user=temporal_indicated
        )

# Singleton Instance
multi_image_context_builder = MultiImageContextBuilder()
