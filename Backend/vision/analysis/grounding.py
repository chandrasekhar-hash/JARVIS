import re
from typing import List, Optional
from vision.models.ui_models import UIObservation, UIElementNode, UIElementType
from tools.logger import log_structured, backend_log

class ElementGroundingEngine:
    def ground_target(
        self,
        query_target: str,
        observation: UIObservation
    ) -> Optional[UIElementNode]:
        """
        Grounds a natural language target description (e.g., 'Retry button', 'File menu', 'Search')
        to a specific UIElementNode with stable spatial coordinates (center_x, center_y).
        Returns None if no matching element is found.
        """
        if not observation.ui_elements or not query_target:
            return None

        target_clean = query_target.lower().strip()
        target_words = set(re.findall(r'\w+', target_clean))

        best_element: Optional[UIElementNode] = None
        best_score = 0.0

        for el in observation.ui_elements:
            if not el.label:
                continue

            label_clean = el.label.lower().strip()
            score = 0.0

            # 1. Exact label match
            if label_clean == target_clean:
                score += 100.0
            # 2. Substring match
            elif target_clean in label_clean or label_clean in target_clean:
                score += 75.0
            else:
                # 3. Word overlap score
                label_words = set(re.findall(r'\w+', label_clean))
                overlap = len(target_words.intersection(label_words))
                if overlap > 0:
                    score += (overlap / max(len(target_words), len(label_words))) * 50.0

            # Boost score if element type matches query keywords
            if el.element_type == UIElementType.BUTTON and ("button" in target_clean or "click" in target_clean):
                score += 15.0
            elif el.element_type == UIElementType.MENU and "menu" in target_clean:
                score += 15.0
            elif el.element_type == UIElementType.INPUT and ("input" in target_clean or "search" in target_clean or "text" in target_clean):
                score += 15.0

            # Apply element confidence weight
            score *= el.confidence

            if score > best_score and score > 20.0:
                best_score = score
                best_element = el

        if best_element:
            log_structured(
                backend_log, 
                "INFO", 
                f"[ElementGrounding] Grounded '{query_target}' -> '{best_element.label}' ({best_element.element_type.value}) at ({best_element.bbox.center_x}, {best_element.bbox.center_y}) [Score: {best_score:.1f}]"
            )
        else:
            log_structured(backend_log, "INFO", f"[ElementGrounding] Target '{query_target}' could not be grounded in UI observation.")

        return best_element

    def get_clickable_elements(self, observation: UIObservation) -> List[UIElementNode]:
        """Returns all elements marked as clickable."""
        return [el for el in observation.ui_elements if el.is_clickable]

    def find_elements_by_type(self, element_type: UIElementType, observation: UIObservation) -> List[UIElementNode]:
        """Returns elements matching a specific UIElementType."""
        return [el for el in observation.ui_elements if el.element_type == element_type]

element_grounding_engine = ElementGroundingEngine()
