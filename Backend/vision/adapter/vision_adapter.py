from typing import Optional, Dict, Any
from vision.pipeline.orchestrator import vision_orchestrator
from vision.context.visual_context import visual_context_manager
from tools.logger import log_structured, backend_log

class VisionAdapter:
    def get_brain_visual_context(
        self,
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes snapshot vision pipeline and translates all visual observation layers
        into a unified, Brain-ready context structure and LLM prompt string.
        """
        pipeline_output = vision_orchestrator.run_snapshot()
        if not pipeline_output:
            return {
                "has_vision": False,
                "reason": "Vision capture permission denied or unavailable",
                "formatted_context": "[Visual Context Unavailable: Permission Denied]"
            }

        frame, ocr_res, ui_obs, scene_obs = pipeline_output
        recent_changes = visual_context_manager.get_recent_changes(limit=3)

        # Build list of clickable grounded UI elements
        ui_summary_items = []
        for el in ui_obs.ui_elements[:10]:
            if el.label:
                ui_summary_items.append(f"'{el.label}' ({el.element_type.value}) at ({el.bbox.center_x}, {el.bbox.center_y})")

        ui_str = ", ".join(ui_summary_items) if ui_summary_items else "No discrete controls detected"
        text_snippet = ocr_res.full_text[:350].replace("\n", " | ") if ocr_res.full_text else "None"
        changes_str = "; ".join([chg.description for chg in recent_changes]) if recent_changes else "Screen layout unchanged"

        # Format clean LLM prompt context block
        formatted = (
            f"[Desktop Visual Screen Context]\n"
            f"Active Application: {scene_obs.summary.active_app.app_name} ({scene_obs.summary.active_app.window_title})\n"
            f"Observable Workflow: {scene_obs.summary.detected_workflow}\n"
            f"Screen Headline: {scene_obs.summary.headline}\n"
            f"Visible Text Summary: {text_snippet}\n"
            f"Grounded UI Controls: {ui_str}\n"
            f"Recent Visual Changes: {changes_str}"
        )

        log_structured(backend_log, "INFO", f"[VisionAdapter] Formatted visual context for Brain (Headline: {scene_obs.summary.headline})")

        return {
            "has_vision": True,
            "formatted_context": formatted,
            "headline": scene_obs.summary.headline,
            "workflow": scene_obs.summary.detected_workflow,
            "active_app": scene_obs.summary.active_app.dict(),
            "full_text": ocr_res.full_text,
            "ui_elements_count": len(ui_obs.ui_elements),
            "recent_changes": [chg.dict() for chg in recent_changes]
        }

vision_adapter = VisionAdapter()
