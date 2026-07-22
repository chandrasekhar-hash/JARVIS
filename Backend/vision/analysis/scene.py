import uuid
import time
import io
import base64
from typing import List, Optional, Tuple
from PIL import Image
from vision.models.capture_models import CaptureFrame
from vision.models.scene_models import (
    SceneObservation,
    SceneSummary,
    ApplicationContext,
    ApplicationCategory
)
from vision.models.ui_models import UIObservation, UIElementType
from vision.analysis.ui import ui_analyzer
from vision.context.visual_context import visual_context_manager
from tools.logger import log_structured, backend_log

class SceneAnalyzer:
    def _classify_application_and_workflow(
        self,
        window_title: Optional[str],
        ui_obs: UIObservation
    ) -> Tuple[ApplicationContext, str]:
        """
        Classifies active application, category, and observable user workflow based on
        window title, process metadata, and visible UI element texts.
        """
        w_title = window_title or "Desktop Environment"
        t_lower = w_title.lower()

        # Collect text from UI elements for context clues
        all_text = " ".join([el.label or "" for el in ui_obs.ui_elements]).lower()
        combined_text = f"{t_lower} {all_text}"

        app_name = "Desktop"
        category = ApplicationCategory.GENERAL
        workflow = "General Desktop Activity"

        # 1. Coding & Development (High priority)
        if any(k in combined_text for k in ["visual studio", "vs code", "code editor", ".py", ".rs", ".js", ".html", "github", "git", "pycharm", "main.py", "editor.py", "workspace"]):
            app_name = "VS Code" if ("vs code" in combined_text or "visual studio" in combined_text) else "Code Editor"
            category = ApplicationCategory.CODING
            workflow = "Software Development & Coding"

        # 2. Command Line / Terminal
        elif any(k in combined_text for k in ["terminal", "powershell", "cmd", "bash", "zsh", "prompt"]):
            app_name = "Terminal"
            category = ApplicationCategory.TERMINAL
            workflow = "Command Line & Systems Management"

        # 3. Web Browsing & Documentation
        elif any(k in combined_text for k in ["chrome", "firefox", "edge", "browser", "http", "https", "react.dev", "docs"]):
            app_name = "Web Browser"
            category = ApplicationCategory.BROWSING
            workflow = "Web Browsing & Research"

        # 4. System Settings
        elif any(k in combined_text for k in ["settings", "control panel", "preferences", "configuration"]):
            app_name = "System Settings"
            category = ApplicationCategory.SETTINGS
            workflow = "System Configuration & Settings"

        # 5. File Management
        elif any(k in combined_text for k in ["file explorer", "explorer", "folder", "downloads", "documents"]):
            app_name = "File Explorer"
            category = ApplicationCategory.FILE_MANAGEMENT
            workflow = "File Navigation & Management"

        app_context = ApplicationContext(
            app_name=app_name,
            window_title=w_title,
            category=category,
            is_focused=True
        )

        return app_context, workflow

    def analyze_scene(self, image: Image.Image, frame_id: Optional[str] = None) -> SceneObservation:
        """
        Analyzes full screen scene context, combining UI understanding, OCR text,
        application classification, workflow detection, and visual change tracking.
        """
        t0 = time.time()
        obs_id = f"scene_{uuid.uuid4().hex[:8]}"

        # 1. UI Understanding & Layout Analysis (Milestone 3.3)
        ui_obs: UIObservation = ui_analyzer.analyze_image(image, frame_id=frame_id)

        # 2. Application & Workflow Classification
        app_ctx, workflow_name = self._classify_application_and_workflow(
            ui_obs.active_window_title,
            ui_obs
        )

        # 3. Detect Dialogs & Error Banners
        has_dialogs = any(el.element_type == UIElementType.DIALOG for el in ui_obs.ui_elements)
        has_errors = any("error" in (el.label or "").lower() or "failed" in (el.label or "").lower() for el in ui_obs.ui_elements)

        summary = SceneSummary(
            headline=f"User active in {app_ctx.app_name} ({app_ctx.window_title})",
            detected_workflow=workflow_name,
            active_app=app_ctx,
            open_windows_count=ui_obs.window_count,
            has_dialogs=has_dialogs,
            has_errors=has_errors
        )

        scene_obs = SceneObservation(
            observation_id=obs_id,
            frame_id=frame_id,
            timestamp=time.time(),
            summary=summary,
            all_windows=[app_ctx],
            recent_changes=[]
        )

        # 4. Push to Visual Context Manager (Calculates change deltas & history timeline)
        changes = visual_context_manager.push_observation(scene_obs)
        scene_obs.recent_changes = changes

        elapsed = time.time() - t0
        log_structured(backend_log, "INFO", f"[SceneAnalyzer] Scene analyzed ({summary.headline}) in {elapsed:.3f}s")

        return scene_obs

    def analyze_frame(self, frame: CaptureFrame) -> SceneObservation:
        """Analyzes a CaptureFrame object directly."""
        if not frame.base64_data:
            dummy_app = ApplicationContext(
                app_name="Desktop",
                window_title="Unknown",
                category=ApplicationCategory.GENERAL
            )
            return SceneObservation(
                observation_id=f"scene_{uuid.uuid4().hex[:8]}",
                frame_id=frame.frame_id,
                timestamp=time.time(),
                summary=SceneSummary(
                    headline="Idle Desktop",
                    detected_workflow="Idle",
                    active_app=dummy_app,
                    open_windows_count=0
                ),
                all_windows=[dummy_app],
                recent_changes=[]
            )

        img_bytes = base64.b64decode(frame.base64_data)
        img = Image.open(io.BytesIO(img_bytes))
        return self.analyze_scene(img, frame_id=frame.frame_id)

scene_analyzer = SceneAnalyzer()
