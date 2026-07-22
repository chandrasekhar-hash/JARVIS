import uuid
import time
import io
import base64
from typing import List, Optional, Tuple, Dict, Any
from PIL import Image, ImageOps, ImageStat
from vision.models.capture_models import CaptureFrame
from vision.models.ui_models import (
    UIObservation,
    UIElementNode,
    UIBoundingBox,
    UIElementType
)
from vision.models.ocr_models import OCRResult, TextElement
from vision.analysis.ocr import ocr_engine
from tools.logger import log_structured, backend_log

class UIAnalyzer:
    def _detect_ui_contours(self, image: Image.Image) -> List[Tuple[int, int, int, int, str]]:
        """
        Detects visual rectangular interface contours (Buttons, Inputs, Windows, Icons).
        Returns list of tuples: (x, y, width, height, detected_type_str)
        """
        detected: List[Tuple[int, int, int, int, str]] = []
        w, h = image.size

        # High-level window node covering full active area
        detected.append((0, 0, w, h, "window"))

        # 1. OpenCV Contour Detector (if available)
        try:
            import cv2
            import numpy as np

            img_np = np.array(image.convert("RGB"))
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
            edged = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edged, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            for c in contours:
                x, y, cw, ch = cv2.boundingRect(c)
                if cw > 30 and ch > 15 and (cw < w * 0.95 or ch < h * 0.95):
                    aspect_ratio = cw / float(ch)
                    if 1.5 <= aspect_ratio <= 8.0 and ch <= 60:
                        detected.append((x, y, cw, ch, "button"))
                    elif aspect_ratio > 8.0 and ch <= 50:
                        detected.append((x, y, cw, ch, "input"))
                    elif 0.8 <= aspect_ratio <= 1.2 and cw <= 50:
                        detected.append((x, y, cw, ch, "icon"))
                    elif cw > 200 and ch > 100:
                        detected.append((x, y, cw, ch, "dialog"))
            return detected
        except Exception:
            pass

        # 2. Native PIL Bounding Box Scanner (Zero-dependency fallback)
        try:
            # Simple native edge threshold scan to detect rectangular regions
            gray = image.convert("L")
            bbox = gray.getbbox()
            if bbox:
                bx, by, bw, bh = bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1]
                if 30 < bw < w and 15 < bh < h:
                    detected.append((bx, by, bw, bh, "button"))
        except Exception:
            pass

        return detected

    def _get_active_window_info(self) -> Tuple[Optional[str], Optional[str]]:
        """Retrieves active window title and process name if available."""
        title: Optional[str] = None
        process: Optional[str] = None
        try:
            import pygetwindow as gw
            w = gw.getActiveWindow()
            if w and w.title:
                title = w.title
        except Exception:
            pass
        return title, process

    def analyze_image(self, image: Image.Image, frame_id: Optional[str] = None) -> UIObservation:
        """
        Analyzes a screen image buffer, detecting UI controls (buttons, inputs, windows, menus),
        and linking OCR text labels to UI element spatial bounding boxes.
        """
        t0 = time.time()
        obs_id = f"obs_{uuid.uuid4().hex[:8]}"

        # 1. OCR Text Extraction (Milestone 3.2)
        ocr_res: OCRResult = ocr_engine.extract_text_from_image(image, frame_id=frame_id)

        # 2. UI Contour Detection
        raw_contours = self._detect_ui_contours(image)

        # 3. Combine OCR text elements with UI contours
        ui_nodes: List[UIElementNode] = []
        window_title, process_name = self._get_active_window_info()

        # Add OCR text elements as UI elements (Labels, Links, Buttons, Menus)
        for text_el in ocr_res.detected_elements:
            bx = text_el.bbox
            txt_lower = text_el.text.lower().strip()

            # Determine element type based on text keywords & position
            elem_type = UIElementType.BUTTON
            if any(k in txt_lower for k in ["file", "edit", "view", "window", "help", "tools", "options"]):
                elem_type = UIElementType.MENU
            elif any(k in txt_lower for k in ["http", "https", "www.", ".com", ".org"]):
                elem_type = UIElementType.LINK
            elif any(k in txt_lower for k in ["search", "enter", "type", "input"]):
                elem_type = UIElementType.INPUT
            else:
                elem_type = UIElementType.BUTTON

            node = UIElementNode(
                element_id=f"ui_{uuid.uuid4().hex[:8]}",
                element_type=elem_type,
                label=text_el.text,
                bbox=UIBoundingBox(
                    x=bx.x,
                    y=bx.y,
                    width=bx.width,
                    height=bx.height,
                    center_x=bx.center_x,
                    center_y=bx.center_y
                ),
                confidence=text_el.confidence,
                is_clickable=True,
                parent_window=window_title,
                application=process_name,
                hierarchy_level=2
            )
            ui_nodes.append(node)

        # Add detected UI shape contours
        for idx, (cx, cy, cw, ch, ctype) in enumerate(raw_contours, 1):
            t_enum = UIElementType.WINDOW
            if ctype == "button":
                t_enum = UIElementType.BUTTON
            elif ctype == "input":
                t_enum = UIElementType.INPUT
            elif ctype == "icon":
                t_enum = UIElementType.ICON
            elif ctype == "dialog":
                t_enum = UIElementType.DIALOG

            node = UIElementNode(
                element_id=f"ui_shape_{idx}_{uuid.uuid4().hex[:6]}",
                element_type=t_enum,
                label=f"{ctype.capitalize()} Control",
                bbox=UIBoundingBox(
                    x=cx,
                    y=cy,
                    width=cw,
                    height=ch,
                    center_x=cx + (cw // 2),
                    center_y=cy + (ch // 2)
                ),
                confidence=0.85,
                is_clickable=(ctype in ["button", "input", "icon"]),
                parent_window=window_title,
                application=process_name,
                hierarchy_level=1 if ctype == "window" else 2
            )
            ui_nodes.append(node)

        elapsed = time.time() - t0
        log_structured(backend_log, "INFO", f"[UIAnalyzer] Analyzed UI layout ({len(ui_nodes)} elements) in {elapsed:.3f}s")

        return UIObservation(
            observation_id=obs_id,
            frame_id=frame_id,
            timestamp=time.time(),
            active_window_title=window_title,
            active_process_name=process_name,
            ui_elements=ui_nodes,
            window_count=1,
            processing_time_seconds=round(elapsed, 3)
        )

    def analyze_frame(self, frame: CaptureFrame) -> UIObservation:
        """Analyzes a CaptureFrame object directly."""
        if not frame.base64_data:
            return UIObservation(
                observation_id=f"obs_{uuid.uuid4().hex[:8]}",
                frame_id=frame.frame_id,
                timestamp=time.time(),
                ui_elements=[],
                window_count=0,
                processing_time_seconds=0.0
            )

        img_bytes = base64.b64decode(frame.base64_data)
        img = Image.open(io.BytesIO(img_bytes))
        return self.analyze_image(img, frame_id=frame.frame_id)

ui_analyzer = UIAnalyzer()
