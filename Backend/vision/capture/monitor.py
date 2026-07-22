import sys
from typing import List, Optional
from vision.models.capture_models import DisplayInfo
from tools.logger import log_structured, backend_log

class MonitorManager:
    def get_monitors(self) -> List[DisplayInfo]:
        """Enumerates connected physical and virtual displays."""
        monitors: List[DisplayInfo] = []
        try:
            import mss
            with mss.mss() as sct:
                # sct.monitors[0] is the bounding box of all monitors combined
                # sct.monitors[1...] are individual physical displays
                for idx, m in enumerate(sct.monitors[1:], 1):
                    monitors.append(
                        DisplayInfo(
                            index=idx,
                            is_primary=(idx == 1),
                            x=m["left"],
                            y=m["top"],
                            width=m["width"],
                            height=m["height"],
                            name=f"Display {idx}"
                        )
                    )
        except Exception as e:
            log_structured(backend_log, "WARNING", f"[MonitorManager] mss display enumeration error: {str(e)}. Using fallback.")
            try:
                import pyautogui
                width, height = pyautogui.size()
                monitors.append(
                    DisplayInfo(
                        index=1,
                        is_primary=True,
                        x=0,
                        y=0,
                        width=width,
                        height=height,
                        name="Primary Display"
                    )
                )
            except Exception as e_fallback:
                log_structured(backend_log, "ERROR", f"[MonitorManager] Fallback enumeration error: {str(e_fallback)}")
                monitors.append(
                    DisplayInfo(
                        index=1,
                        is_primary=True,
                        x=0,
                        y=0,
                        width=1920,
                        height=1080,
                        name="Default Display"
                    )
                )

        return monitors

    def get_primary_monitor(self) -> DisplayInfo:
        """Returns metadata for the primary display."""
        monitors = self.get_monitors()
        for m in monitors:
            if m.is_primary:
                return m
        return monitors[0] if monitors else DisplayInfo(index=1, is_primary=True, x=0, y=0, width=1920, height=1080, name="Default")

    def get_monitor_by_index(self, index: int) -> Optional[DisplayInfo]:
        """Returns display metadata for a target index."""
        monitors = self.get_monitors()
        for m in monitors:
            if m.index == index:
                return m
        return None

monitor_manager = MonitorManager()
