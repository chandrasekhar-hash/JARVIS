import uuid
from typing import List, Dict, Any, Tuple
from vision.models.ocr_models import TextElement, TextBoundingBox
from tools.logger import log_structured, backend_log

class TextMapper:
    def map_and_order_text(
        self,
        raw_detections: List[Tuple[int, int, int, int, str, float]],
        language: str = "en"
    ) -> List[TextElement]:
        """
        Sorts raw text detections into natural top-to-bottom, left-to-right reading order.
        Groups items into lines (tolerance y <= 12px) and paragraphs (gap y > 25px).
        Input format for each detection: (x, y, width, height, text_str, confidence_float)
        """
        if not raw_detections:
            return []

        # Sort primarily by y (top to bottom), then x (left to right)
        sorted_raw = sorted(raw_detections, key=lambda d: (d[1], d[0]))

        elements: List[TextElement] = []
        current_line = 1
        current_paragraph = 1
        last_y = None
        last_x = None

        for idx, (x, y, w, h, text, conf) in enumerate(sorted_raw, 1):
            if last_y is not None:
                # Line grouping tolerance
                if abs(y - last_y) > 12:
                    current_line += 1
                    # Paragraph gap tolerance
                    if abs(y - last_y) > 28:
                        current_paragraph += 1

            last_y = y
            last_x = x

            center_x = x + (w // 2)
            center_y = y + (h // 2)

            bbox = TextBoundingBox(
                x=x,
                y=y,
                width=w,
                height=h,
                center_x=center_x,
                center_y=center_y
            )

            el = TextElement(
                text_id=f"text_{uuid.uuid4().hex[:8]}",
                text=text.strip(),
                bbox=bbox,
                confidence=round(conf, 3),
                line_number=current_line,
                paragraph_id=current_paragraph,
                reading_order=idx,
                language=language
            )
            elements.append(el)

        log_structured(backend_log, "INFO", f"[TextMapper] Mapped {len(elements)} text elements into {current_line} lines and {current_paragraph} paragraphs")
        return elements

text_mapper = TextMapper()
