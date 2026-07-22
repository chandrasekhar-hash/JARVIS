import uuid
import time
from typing import List, Optional
from vision.models.scene_models import (
    SceneObservation,
    VisualChange,
    VisualChangeType
)
from tools.logger import log_structured, backend_log

class ChangeDetector:
    def detect_changes(
        self,
        prev_obs: Optional[SceneObservation],
        curr_obs: SceneObservation
    ) -> List[VisualChange]:
        """
        Compares a previous SceneObservation with the current SceneObservation
        and returns a list of detected visual change events.
        """
        changes: List[VisualChange] = []
        now = time.time()

        if prev_obs is None:
            changes.append(
                VisualChange(
                    change_id=f"chg_{uuid.uuid4().hex[:8]}",
                    timestamp=now,
                    change_type=VisualChangeType.WINDOW_OPENED,
                    description=f"Initial observation: {curr_obs.summary.active_app.app_name} ({curr_obs.summary.active_app.window_title})"
                )
            )
            return changes

        p_app = prev_obs.summary.active_app
        c_app = curr_obs.summary.active_app

        # 1. Application or Window Title Switch
        if p_app.app_name != c_app.app_name or p_app.window_title != c_app.window_title:
            changes.append(
                VisualChange(
                    change_id=f"chg_{uuid.uuid4().hex[:8]}",
                    timestamp=now,
                    change_type=VisualChangeType.APP_SWITCHED,
                    description=f"Switched from '{p_app.app_name}' to '{c_app.app_name}' ({c_app.window_title})"
                )
            )

        # 2. Window count changes
        if curr_obs.summary.open_windows_count > prev_obs.summary.open_windows_count:
            changes.append(
                VisualChange(
                    change_id=f"chg_{uuid.uuid4().hex[:8]}",
                    timestamp=now,
                    change_type=VisualChangeType.WINDOW_OPENED,
                    description="New window opened"
                )
            )
        elif curr_obs.summary.open_windows_count < prev_obs.summary.open_windows_count:
            changes.append(
                VisualChange(
                    change_id=f"chg_{uuid.uuid4().hex[:8]}",
                    timestamp=now,
                    change_type=VisualChangeType.WINDOW_CLOSED,
                    description="Window closed"
                )
            )

        # 3. Dialog or Notification Appearance
        if not prev_obs.summary.has_dialogs and curr_obs.summary.has_dialogs:
            changes.append(
                VisualChange(
                    change_id=f"chg_{uuid.uuid4().hex[:8]}",
                    timestamp=now,
                    change_type=VisualChangeType.DIALOG_APPEARED,
                    description="System dialog or modal popup appeared on screen"
                )
            )

        # 4. Error state appearance
        if not prev_obs.summary.has_errors and curr_obs.summary.has_errors:
            changes.append(
                VisualChange(
                    change_id=f"chg_{uuid.uuid4().hex[:8]}",
                    timestamp=now,
                    change_type=VisualChangeType.NOTIFICATION_APPEARED,
                    description="Error banner or alert notification detected on screen"
                )
            )

        # 5. Fallback: Screen Unchanged
        if not changes:
            changes.append(
                VisualChange(
                    change_id=f"chg_{uuid.uuid4().hex[:8]}",
                    timestamp=now,
                    change_type=VisualChangeType.SCREEN_UNCHANGED,
                    description="Screen visual layout remains unchanged"
                )
            )

        log_structured(backend_log, "INFO", f"[ChangeDetector] Detected {len(changes)} visual change events")
        return changes

change_detector = ChangeDetector()
