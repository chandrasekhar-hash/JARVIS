from typing import Dict, Any
from vision.models.capture_models import CapturePermissionState
from tools.logger import log_structured, backend_log

class VisionPermissionManager:
    def __init__(self):
        self._state: CapturePermissionState = CapturePermissionState.ALWAYS_ALLOW

    @property
    def current_state(self) -> CapturePermissionState:
        return self._state

    def set_permission(self, state: CapturePermissionState) -> None:
        """Sets current capture permission state."""
        self._state = state
        log_structured(backend_log, "INFO", f"[VisionPermission] Permission set to '{self._state.value}'")

    def grant_allow_once(self) -> None:
        self.set_permission(CapturePermissionState.ALLOW_ONCE)

    def grant_always_allow(self) -> None:
        self.set_permission(CapturePermissionState.ALWAYS_ALLOW)

    def deny_permission(self) -> None:
        self.set_permission(CapturePermissionState.DENIED)

    def verify_capture_allowed(self) -> bool:
        """
        Verifies if capture is authorized.
        Consumes 'ALLOW_ONCE' state upon verification.
        """
        if self._state == CapturePermissionState.DENIED:
            log_structured(backend_log, "WARNING", "[VisionPermission] Capture attempt blocked: Permission DENIED.")
            return False

        if self._state == CapturePermissionState.ALLOW_ONCE:
            log_structured(backend_log, "INFO", "[VisionPermission] Consuming ALLOW_ONCE permission for current frame.")
            self._state = CapturePermissionState.DENIED  # Consumed
            return True

        if self._state == CapturePermissionState.ALWAYS_ALLOW:
            return True

        return False

vision_permission_manager = VisionPermissionManager()
