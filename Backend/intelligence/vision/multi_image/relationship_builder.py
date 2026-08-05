import re
from typing import List, Dict, Any, Optional

from intelligence.vision.multi_image.models import (
    RelationshipTag, ImageRelationshipItem, StructuredComparison, MultiImageResult, MultiImageContext
)
from tools.telemetry import log_structured, backend_log

class RelationshipBuilder:
    """
    Relationship Builder & Normalizer (V6).
    Parses and normalizes Gemini's multimodal cross-image reasoning output into:
    - Structured ImageRelationshipItem list with RelationshipTag enums
    - StructuredComparison object (additions, removals, modifications, ranking, inconsistencies, etc.)
    - Clean user-facing text and bounded visual summary
    """

    def _parse_tag(self, raw_tag: str) -> RelationshipTag:
        clean = raw_tag.strip().lower().replace("[", "").replace("]", "")
        for tag in RelationshipTag:
            if tag.value in clean:
                return tag
        return RelationshipTag.MODIFIED if "differ" in clean or "change" in clean else RelationshipTag.UNKNOWN

    def parse_gemini_output(
        self,
        raw_text: str,
        context: MultiImageContext,
        model_name: str
    ) -> MultiImageResult:
        if not raw_text:
            return MultiImageResult(
                text="No multi-image analysis response was generated.",
                task_type=context.task.value,
                image_count=context.image_count,
                relationships=[],
                structured_comparison=StructuredComparison(summary="No analysis output."),
                ocr_used=context.requires_ocr,
                visual_summary="Empty response."
            )

        # 1. Extract visual summary at the end
        visual_summary = "Multi-image comparison complete."
        summary_match = re.search(r"\[VISUAL SUMMARY:\s*(.*?)\]$", raw_text, re.DOTALL | re.IGNORECASE)
        working_text = raw_text
        if summary_match:
            visual_summary = re.sub(r"\s+", " ", summary_match.group(1)).strip()[:200]
            working_text = working_text[:summary_match.start()].strip()

        # 2. Extract structured data block
        structured_comp = StructuredComparison()
        relationships: List[ImageRelationshipItem] = []

        struct_match = re.search(r"<MULTIMEDIA_STRUCTURED_DATA>(.*?)</MULTIMEDIA_STRUCTURED_DATA>", working_text, re.DOTALL | re.IGNORECASE)
        clean_user_text = working_text

        if struct_match:
            struct_content = struct_match.group(1).strip()
            clean_user_text = working_text[:struct_match.start()].strip() + working_text[struct_match.end():].strip()
            clean_user_text = re.sub(r"\n{3,}", "\n\n", clean_user_text).strip()

            # Parse lines in structured block
            lines = [l.strip() for l in struct_content.split("\n") if l.strip()]
            current_section = None

            for line in lines:
                if line.startswith("- Image ") or (" Image " in line and " -> " in line):
                    # Relationship entry: "- Image 1 -> Image 2: [modified] | changed layout"
                    rel_match = re.search(r"Image\s*(\d+)\s*(?:->|vs|to)\s*Image\s*(\d+)[:\s]*\[?(.*?)\]?\s*(?:\||\-)(.*)", line, re.IGNORECASE)
                    if rel_match:
                        img1, img2, tag_str, details = rel_match.groups()
                        tag = self._parse_tag(tag_str)
                        relationships.append(ImageRelationshipItem(
                            pair=f"Image {img1} -> Image {img2}",
                            relationship=tag,
                            details=details.strip()
                        ))
                    continue

                if line.startswith("SUMMARY:"):
                    structured_comp.summary = line.replace("SUMMARY:", "").strip()
                elif line.startswith("ADDITIONS:"):
                    val = line.replace("ADDITIONS:", "").strip()
                    if val and val.lower() != "none":
                        structured_comp.additions = [x.strip() for x in val.split(";") if x.strip()]
                elif line.startswith("REMOVALS:"):
                    val = line.replace("REMOVALS:", "").strip()
                    if val and val.lower() != "none":
                        structured_comp.removals = [x.strip() for x in val.split(";") if x.strip()]
                elif line.startswith("MODIFICATIONS:"):
                    val = line.replace("MODIFICATIONS:", "").strip()
                    if val and val.lower() != "none":
                        structured_comp.modifications = [x.strip() for x in val.split(";") if x.strip()]
                elif line.startswith("REORDERINGS:"):
                    val = line.replace("REORDERINGS:", "").strip()
                    if val and val.lower() != "none":
                        structured_comp.reorderings = [x.strip() for x in val.split(";") if x.strip()]
                elif line.startswith("RANKING:"):
                    val = line.replace("RANKING:", "").strip()
                    if val and val.lower() != "none":
                        items = val.split(";")
                        for idx, item in enumerate(items, start=1):
                            structured_comp.ranking.append({"rank": idx, "description": item.strip()})
                elif line.startswith("RANKING_CRITERIA:"):
                    val = line.replace("RANKING_CRITERIA:", "").strip()
                    if val and val.lower() != "none":
                        structured_comp.ranking_criteria = val
                elif line.startswith("INCONSISTENCIES:"):
                    val = line.replace("INCONSISTENCIES:", "").strip()
                    if val and val.lower() != "none":
                        structured_comp.inconsistencies = [x.strip() for x in val.split(";") if x.strip()]
                elif line.startswith("DUPLICATES:"):
                    val = line.replace("DUPLICATES:", "").strip()
                    if val and val.lower() != "none":
                        structured_comp.duplicates = [x.strip() for x in val.split(";") if x.strip()]
                elif line.startswith("CHRONOLOGY:"):
                    val = line.replace("CHRONOLOGY:", "").strip()
                    if "INFERRED" in val.upper():
                        structured_comp.chronology_inferred = True
                    structured_comp.chronology_explanation = val
                elif line.startswith("BEST_CHOICE:"):
                    val = line.replace("BEST_CHOICE:", "").strip()
                    if val and val.lower() != "none":
                        structured_comp.best_choice = val

        # 3. Fallback relationships generation if Gemini did not include structured block
        if not relationships and context.image_count >= 2:
            for idx in range(1, context.image_count):
                rel_tag = RelationshipTag.SAME if (context.is_exact_duplicates and [idx, idx+1] in context.duplicate_pairs) else RelationshipTag.DIFFERENT
                relationships.append(ImageRelationshipItem(
                    pair=f"Image {idx} -> Image {idx+1}",
                    relationship=rel_tag,
                    details="Cross-image relationship analyzed by Gemini Vision."
                ))

        if not structured_comp.summary:
            structured_comp.summary = visual_summary

        return MultiImageResult(
            text=clean_user_text,
            task_type=context.task.value,
            image_count=context.image_count,
            relationships=relationships,
            structured_comparison=structured_comp,
            ocr_used=context.requires_ocr,
            visual_summary=visual_summary,
            metadata={
                "task_hint": context.task.value,
                "is_duplicates": context.is_exact_duplicates,
                "duplicate_pairs": context.duplicate_pairs,
                "temporal_indicated": context.temporal_indicated_by_user
            }
        )

# Singleton Instance
relationship_builder = RelationshipBuilder()
