import asyncio
import time
from typing import Optional, Dict, Any, Callable, List
from vision.models.capture_models import (
    VisionState,
    CaptureTarget,
    CaptureFrame,
    CaptureMode
)
from vision.capture.engine import capture_engine
from vision.capture.permissions import vision_permission_manager, CapturePermissionState
from tools.logger import log_structured, backend_log

class VisionServiceManager:
    def __init__(self):
        self._state: VisionState = VisionState.STOPPED
        self._fps: float = 1.0
        self._target: CaptureTarget = CaptureTarget(mode=CaptureMode.SNAPSHOT, monitor_index=1)
        self._worker_task: Optional[asyncio.Task] = None
        self._last_frame: Optional[CaptureFrame] = None
        self._frame_listeners: List[Callable[[CaptureFrame], None]] = []

    @property
    def state(self) -> VisionState:
        return self._state

    @property
    def is_active(self) -> bool:
        return self._state == VisionState.RUNNING

    def add_frame_listener(self, listener: Callable[[CaptureFrame], None]) -> None:
        """Subscribes a listener callback to receive newly captured frames."""
        if listener not in self._frame_listeners:
            self._frame_listeners.append(listener)

    def remove_frame_listener(self, listener: Callable[[CaptureFrame], None]) -> None:
        if listener in self._frame_listeners:
            self._frame_listeners.remove(listener)

    def capture_snapshot(self, target: Optional[CaptureTarget] = None) -> Optional[CaptureFrame]:
        """Captures a single snapshot frame on demand."""
        frame = capture_engine.capture_frame(target or self._target)
        if frame:
            self._last_frame = frame
            for listener in self._frame_listeners:
                try:
                    listener(frame)
                except Exception as e:
                    log_structured(backend_log, "WARNING", f"[VisionManager] Listener error: {str(e)}")
        return frame

    def start_vision(self, target: Optional[CaptureTarget] = None, fps: float = 1.0) -> bool:
        """Starts continuous vision capture stream at requested FPS."""
        if self._state == VisionState.RUNNING:
            log_structured(backend_log, "INFO", "[VisionManager] Vision service already running.")
            return True

        if target:
            self._target = target
        self._target.mode = CaptureMode.CONTINUOUS
        self._fps = max(0.1, min(10.0, fps))  # Clamp FPS between 0.1 and 10.0
        self._state = VisionState.RUNNING

        log_structured(backend_log, "INFO", f"[VisionManager] Vision service started (FPS={self._fps}, Monitor={self._target.monitor_index})")
        
        # Launch continuous async worker loop
        try:
            loop = asyncio.get_running_loop()
            self._worker_task = loop.create_task(self._continuous_capture_loop())
        except RuntimeError:
            pass  # Will be managed synchronously or when event loop starts

        return True

    async def _continuous_capture_loop(self):
        """Internal background loop for continuous frame capture."""
        interval = 1.0 / self._fps
        while self._state in [VisionState.RUNNING, VisionState.PAUSED]:
            if self._state == VisionState.RUNNING:
                frame = self.capture_snapshot(self._target)
            await asyncio.sleep(interval)

    def pause_vision(self) -> bool:
        """Pauses the active vision stream."""
        if self._state == VisionState.RUNNING:
            self._state = VisionState.PAUSED
            log_structured(backend_log, "INFO", "[VisionManager] Vision service PAUSED.")
            return True
        return False

    def resume_vision(self) -> bool:
        """Resumes a paused vision stream."""
        if self._state == VisionState.PAUSED:
            self._state = VisionState.RUNNING
            log_structured(backend_log, "INFO", "[VisionManager] Vision service RESUMED.")
            return True
        return False

    def stop_vision(self) -> bool:
        """Stops vision service and cancels worker task."""
        self._state = VisionState.STOPPED
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            self._worker_task = None
        self._last_frame = None
        log_structured(backend_log, "INFO", "[VisionManager] Vision service STOPPED.")
        return True

    def get_service_status(self) -> Dict[str, Any]:
        """Returns metadata status of Vision service."""
        return {
            "state": self._state.value,
            "fps": self._fps,
            "permission_level": vision_permission_manager.current_state.value,
            "target": self._target.dict(),
            "has_last_frame": self._last_frame is not None,
            "last_frame_id": self._last_frame.frame_id if self._last_frame else None
        }

vision_service_manager = VisionServiceManager()
