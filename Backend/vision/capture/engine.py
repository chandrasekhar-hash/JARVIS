import uuid
import time
import io
import ctypes
import base64
import hashlib
from typing import Optional, Dict, Any
from PIL import Image, ImageGrab
from vision.models.capture_models import (
    CaptureTarget,
    CaptureFrame,
    BoundingBox,
    CaptureMode
)
from vision.capture.monitor import monitor_manager
from vision.capture.permissions import vision_permission_manager
from tools.logger import log_structured, backend_log

class CaptureEngine:
    def __init__(self):
        self._last_frame_hash: Optional[str] = None

    def _hash_image_bytes(self, img_bytes: bytes) -> str:
        """Computes MD5 hash of image bytes for change detection."""
        return hashlib.md5(img_bytes).hexdigest()

    def _apply_sensitive_masking(self, image: Image.Image) -> Image.Image:
        """Integration hook for sensitive region masking."""
        return image

    def _grab_win32_gdi(self, x: int, y: int, width: int, height: int) -> Optional[Image.Image]:
        """Captures screen using low-level Windows GDI BitBlt calls via ctypes."""
        try:
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32

            hwnd = user32.GetDesktopWindow()
            hwnd_dc = user32.GetWindowDC(hwnd)
            mfc_dc = gdi32.CreateCompatibleDC(hwnd_dc)
            save_bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
            gdi32.SelectObject(mfc_dc, save_bitmap)

            # BitBlt SRCCOPY (0x00CC0020)
            gdi32.BitBlt(mfc_dc, 0, 0, width, height, hwnd_dc, x, y, 0x00CC0020)

            # Convert to PIL Image via bitmap info header
            class BITMAPINFOHEADER(ctypes.Structure):
                _fields_ = [
                    ('biSize', ctypes.c_uint32),
                    ('biWidth', ctypes.c_int32),
                    ('biHeight', ctypes.c_int32),
                    ('biPlanes', ctypes.c_uint16),
                    ('biBitCount', ctypes.c_uint16),
                    ('biCompression', ctypes.c_uint32),
                    ('biSizeImage', ctypes.c_uint32),
                    ('biXPelsPerMeter', ctypes.c_int32),
                    ('biYPelsPerMeter', ctypes.c_int32),
                    ('biClrUsed', ctypes.c_uint32),
                    ('biClrImportant', ctypes.c_uint32)
                ]

            bmi = BITMAPINFOHEADER()
            bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.biWidth = width
            bmi.biHeight = -height  # top-down
            bmi.biPlanes = 1
            bmi.biBitCount = 32
            bmi.biCompression = 0

            buffer = ctypes.create_string_buffer(width * height * 4)
            gdi32.GetDIBits(hwnd_dc, save_bitmap, 0, height, buffer, ctypes.byref(bmi), 0)

            gdi32.DeleteObject(save_bitmap)
            gdi32.DeleteDC(mfc_dc)
            user32.ReleaseDC(hwnd, hwnd_dc)

            return Image.frombytes("RGBA", (width, height), buffer.raw, "raw", "BGRA").convert("RGB")
        except Exception:
            return None

    def capture_frame(self, target: Optional[CaptureTarget] = None) -> Optional[CaptureFrame]:
        """
        Captures a single screen frame based on target monitor/region and permission state.
        Returns a memory-safe CaptureFrame or synthetic fallback frame in headless test modes.
        """
        if not vision_permission_manager.verify_capture_allowed():
            log_structured(backend_log, "WARNING", "[CaptureEngine] Frame capture skipped: Permission not granted.")
            return None

        if target is None:
            target = CaptureTarget(mode=CaptureMode.SNAPSHOT, monitor_index=1)

        disp = monitor_manager.get_monitor_by_index(target.monitor_index) or monitor_manager.get_primary_monitor()

        t0 = time.time()
        img: Optional[Image.Image] = None

        # 1. Native ImageGrab (Pillow)
        try:
            img = ImageGrab.grab()
        except Exception:
            pass

        # 2. Windows GDI BitBlt
        if img is None and ctypes.sizeof(ctypes.c_void_p) == 8:
            img = self._grab_win32_gdi(disp.x, disp.y, disp.width, disp.height)

        # 3. mss Fallback
        if img is None:
            try:
                import mss
                with mss.mss() as sct:
                    monitor_rect = {"left": disp.x, "top": disp.y, "width": disp.width, "height": disp.height}
                    sct_img = sct.grab(monitor_rect)
                    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            except Exception:
                pass

        # 4. PyAutoGUI Fallback
        if img is None:
            try:
                import pyautogui
                img = pyautogui.screenshot()
            except Exception:
                pass

        # 5. Headless Synthetic Test Frame Fallback
        if img is None:
            log_structured(backend_log, "INFO", "[CaptureEngine] OS desktop DC locked/headless mode: Generating synthetic test frame.")
            img = Image.new("RGB", (disp.width, disp.height), color=(30, 30, 30))

        # Handle Region Cropping if specified
        if target.region:
            reg = target.region
            crop_box = (reg.x, reg.y, reg.x + reg.width, reg.y + reg.height)
            img = img.crop(crop_box)

        # Apply sensitive data masking hook
        img = self._apply_sensitive_masking(img)

        # Encode to bytes & base64 in memory
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        img_bytes = buffer.getvalue()

        frame_hash = self._hash_image_bytes(img_bytes)
        has_changed = (frame_hash != self._last_frame_hash)
        self._last_frame_hash = frame_hash

        b64_str = base64.b64encode(img_bytes).decode("utf-8")
        frame_id = f"frame_{uuid.uuid4().hex[:8]}"

        frame = CaptureFrame(
            frame_id=frame_id,
            timestamp=time.time(),
            monitor_index=disp.index,
            resolution={"width": img.width, "height": img.height},
            format="PNG",
            base64_data=b64_str,
            byte_size=len(img_bytes),
            has_changed=has_changed
        )

        elapsed = time.time() - t0
        log_structured(backend_log, "INFO", f"[CaptureEngine] Captured frame {frame_id} ({img.width}x{img.height}, {len(img_bytes)} bytes) in {elapsed:.3f}s")
        return frame

capture_engine = CaptureEngine()
