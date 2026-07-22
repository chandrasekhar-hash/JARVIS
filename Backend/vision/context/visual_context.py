from typing import List, Optional, Dict, Any
from vision.models.scene_models import SceneObservation, VisualChange
from vision.context.change_detector import change_detector
from tools.logger import log_structured, backend_log

class VisualContextManager:
    def __init__(self, max_history: int = 10):
        self._max_history = max_history
        self._scene_history: List[SceneObservation] = []
        self._change_history: List[VisualChange] = []

    def push_observation(self, observation: SceneObservation) -> List[VisualChange]:
        """
        Pushes a new SceneObservation into short-term visual memory.
        Calculates frame deltas, updates change history, and prunes older frames.
        """
        prev_obs = self.get_latest_observation()
        changes = change_detector.detect_changes(prev_obs, observation)

        observation.recent_changes = changes
        self._scene_history.append(observation)
        self._change_history.extend(changes)

        # Prune older history
        if len(self._scene_history) > self._max_history:
            self._scene_history.pop(0)

        if len(self._change_history) > 30:
            self._change_history = self._change_history[-30:]

        log_structured(backend_log, "INFO", f"[VisualContext] Pushed observation {observation.observation_id} (History depth: {len(self._scene_history)})")
        return changes

    def get_latest_observation(self) -> Optional[SceneObservation]:
        """Returns the most recent SceneObservation in memory."""
        return self._scene_history[-1] if self._scene_history else None

    def get_recent_changes(self, limit: int = 5) -> List[VisualChange]:
        """Returns recent visual change events up to specified limit."""
        return self._change_history[-limit:] if self._change_history else []

    def get_active_app_history(self) -> List[str]:
        """Returns timeline list of recently active application names."""
        history: List[str] = []
        for obs in self._scene_history:
            app_name = obs.summary.active_app.app_name
            if not history or history[-1] != app_name:
                history.append(app_name)
        return history

    def clear_context(self) -> None:
        """Clears visual context memory."""
        self._scene_history.clear()
        self._change_history.clear()
        log_structured(backend_log, "INFO", "[VisualContext] Visual context cleared.")

visual_context_manager = VisualContextManager()
