import sys
import os
import io
import time
import unittest
from unittest.mock import patch, MagicMock
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app
from intelligence.vision.models import VisionRequest, VisionResult
from intelligence.vision.ocr.models import OCRResult, OCRImageResult
from intelligence.vision.camera.models import SessionStatus, CameraAnalysisResult
from intelligence.vision.camera.scene_detector import scene_change_detector, SceneChangeDetector
from intelligence.vision.camera.frame_selector import frame_selector
from intelligence.vision.camera.session_manager import session_manager, VisionSessionManager
from intelligence.vision.camera.camera_service import camera_vision_service

client = TestClient(app)

def _make_camera_png(label: str, width=640, height=480, bg=(30, 30, 35), fg=(220, 220, 225)) -> bytes:
    img = Image.new("RGB", (width, height), color=bg)
    draw = ImageDraw.Draw(img)
    lines = label.split("\n")
    y = 20
    for line in lines:
        draw.text((20, y), line, fill=fg)
        y += 25
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

FRAME_ARDUINO_BOARD = _make_camera_png("Camera Stream\nObject: Arduino Mega 2560 Board\nConnected: USB Cable, LED Module", bg=(30, 30, 35))
FRAME_ARDUINO_STABLE = _make_camera_png("Camera Stream\nObject: Arduino Mega 2560 Board\nConnected: USB Cable, LED Module", bg=(30, 30, 35))
FRAME_RECEIPT_LABEL = _make_camera_png("RECEIPT #8821\nStore: Tech Supply Co\nItem: Sensor Module\nPrice: $24.99", bg=(240, 240, 240), fg=(10, 10, 10))
FRAME_MONITOR_VSCODE = _make_camera_png("Monitor View: VS Code\n1: import requests\n2: app = FastAPI()\nPROBLEMS: 0", bg=(15, 15, 20))
FRAME_MOVED_SCENE = _make_camera_png("Camera Panned → Desktop Keyboard & Mouse\nNo Arduino visible", bg=(180, 60, 20), fg=(255, 255, 255))


class TestVisionV7CameraVisionIntelligence(unittest.TestCase):

    def setUp(self):
        # Reset session manager state before each test
        session_manager.sessions.clear()

    # --- 1. SCENE CHANGE DETECTOR TESTS ---
    def test_scene_change_detector_latency_and_decision(self):
        detector = SceneChangeDetector(threshold=0.15)
        
        # Initial frame (no previous frame)
        res1 = detector.evaluate_change(FRAME_ARDUINO_BOARD, None)
        self.assertTrue(res1.should_analyze)
        self.assertEqual(res1.score, 1.0)

        # Identical stable frame
        t0 = time.time()
        res2 = detector.evaluate_change(FRAME_ARDUINO_STABLE, FRAME_ARDUINO_BOARD)
        eval_ms = (time.time() - t0) * 1000
        
        self.assertFalse(res2.should_analyze)
        self.assertLess(res2.score, 0.15)
        self.assertLess(eval_ms, 50.0) # Must execute < 50ms (typically < 5ms)

        # Moved scene frame
        res3 = detector.evaluate_change(FRAME_MOVED_SCENE, FRAME_ARDUINO_BOARD)
        self.assertTrue(res3.should_analyze)
        self.assertGreater(res3.score, 0.05)

    # --- 2. FRAME SELECTOR TESTS ---
    def test_frame_selector_skips_stable_idle_frame(self):
        scene_res = scene_change_detector.evaluate_change(FRAME_ARDUINO_STABLE, FRAME_ARDUINO_BOARD)
        should_proc, reason = frame_selector.should_process_frame(scene_res, user_prompt=None, has_active_focus=True)
        self.assertFalse(should_proc)
        self.assertIn("Skipped", reason)

    def test_frame_selector_selects_user_prompt_even_if_stable(self):
        scene_res = scene_change_detector.evaluate_change(FRAME_ARDUINO_STABLE, FRAME_ARDUINO_BOARD)
        should_proc, reason = frame_selector.should_process_frame(scene_res, user_prompt="What is this?", has_active_focus=True)
        self.assertTrue(should_proc)
        self.assertIn("Trigger:", reason)

    # --- 3. SESSION MANAGER & MEMORY CLEANUP TESTS ---
    def test_session_lifecycle_and_max_keyframes(self):
        session = session_manager.get_or_create_session("test_sess_1")
        self.assertEqual(session.status.value, "ACTIVE")

        # Add 7 keyframes (buffer must retain max 5)
        for i in range(7):
            session.add_keyframe(FRAME_ARDUINO_BOARD)

        self.assertEqual(len(session.keyframes), 5)
        self.assertEqual(session.keyframes[-1].frame_index, 7)

        # Purge session memory
        session_manager.purge_session("test_sess_1")
        self.assertIsNone(session_manager.get_session("test_sess_1"))

    def test_session_auto_timeout_cleanup(self):
        session = session_manager.get_or_create_session("timeout_sess")
        session.last_accessed_at = time.time() - 400 # 400 seconds ago > 300s timeout

        session_manager.cleanup_expired_sessions(timeout_seconds=300)
        self.assertNotIn("timeout_sess", session_manager.sessions)

    # --- 4. FOCUS CONTINUITY & PRONOUN RESOLUTION ---
    @patch("intelligence.vision.providers.gemini_vision.GeminiVisionProvider.analyze")
    def test_camera_service_focus_continuity(self, mock_analyze):
        mock_analyze.return_value = VisionResult(
            text="This is an Arduino Mega 2560 microcontroller board with a blue USB cable.",
            provider="Gemini",
            model="gemini-2.5-flash",
            image_count=1,
            visual_summary="Arduino Mega 2560 microcontroller board."
        )

        import asyncio
        # Turn 1: Initial query
        res1 = asyncio.run(camera_vision_service.process_camera_frame(
            session_id="focus_test_session",
            frame_bytes=FRAME_ARDUINO_BOARD,
            user_prompt="What is this?"
        ))

        session = session_manager.get_session("focus_test_session")
        self.assertIsNotNone(session.active_focus)
        self.assertIn("Arduino", session.active_focus)

        # Turn 2: Follow-up query using pronoun "here"
        mock_analyze.return_value = VisionResult(
            text="Connected to the Arduino board is a red LED module and a USB cable.",
            provider="Gemini",
            model="gemini-2.5-flash",
            image_count=1,
            visual_summary="Connected LED module."
        )

        res2 = asyncio.run(camera_vision_service.process_camera_frame(
            session_id="focus_test_session",
            frame_bytes=FRAME_ARDUINO_STABLE,
            user_prompt="What is connected here?"
        ))

        # Assert context passed active focus
        last_prompt_sent = mock_analyze.call_args[0][0].prompt
        self.assertIn("CONVERSATIONAL FOCUS", last_prompt_sent)
        self.assertIn("Arduino", last_prompt_sent)

    # --- 5. REUSE INTELLIGENCE (OCR, SCREENSHOT, MULTI-IMAGE) ---
    @patch("intelligence.vision.ocr.ocr_service.OCRService.extract")
    def test_camera_ocr_reuse(self, mock_ocr):
        mock_ocr.return_value = OCRResult(
            text="RECEIPT #8821\nTech Supply Co\nTotal: $24.99",
            has_text=True,
            image_count=1,
            images=[OCRImageResult(index=1, text="RECEIPT #8821\nTech Supply Co", has_text=True)],
            provider="Gemini",
            model="gemini-2.5-flash"
        )

        import asyncio
        res = asyncio.run(camera_vision_service.process_camera_frame(
            session_id="ocr_session",
            frame_bytes=FRAME_RECEIPT_LABEL,
            user_prompt="Read this receipt"
        ))

        self.assertEqual(res.task_type, "CAMERA_OCR")
        self.assertIn("RECEIPT #8821", res.text)
        mock_ocr.assert_called_once()

    @patch("intelligence.vision.multi_image.multi_image_service.MultiImageService.analyze_multi_images")
    def test_camera_multi_image_reuse_on_what_changed(self, mock_multi):
        mock_multi.return_value = VisionResult(
            text="Image 1 showed the Arduino board. Image 2 showed the camera panned to the keyboard.",
            provider="Gemini",
            model="gemini-2.5-flash",
            image_count=2,
            task_type="PROGRESS_TRACKING",
            visual_summary="Camera moved from Arduino to keyboard."
        )

        import asyncio
        # Setup 2 keyframes in session
        session = session_manager.get_or_create_session("multi_session")
        session.add_keyframe(FRAME_ARDUINO_BOARD)
        session.add_keyframe(FRAME_MOVED_SCENE)

        res = asyncio.run(camera_vision_service.process_camera_frame(
            session_id="multi_session",
            frame_bytes=FRAME_MOVED_SCENE,
            user_prompt="What changed or moved?"
        ))

        self.assertEqual(res.task_type, "CAMERA_MULTI_IMAGE")
        mock_multi.assert_called_once()

    # --- 6. API ENDPOINTS INTEGRATION TESTS ---
    def test_api_camera_session_start_frame_status_end(self):
        # 1. Start Session
        r_start = client.post("/api/vision/camera/session/start", data={"session_id": "api_test_sess"})
        self.assertEqual(r_start.status_code, 200)
        res_start = r_start.json()
        self.assertEqual(res_start["session_id"], "api_test_sess")

        # 2. Get Status
        r_stat = client.get("/api/vision/camera/session/status?session_id=api_test_sess")
        self.assertEqual(r_stat.status_code, 200)
        res_stat = r_stat.json()
        self.assertEqual(res_stat["session_status"], "ACTIVE")

        # 3. Process Frame
        with patch("intelligence.vision.providers.gemini_vision.GeminiVisionProvider.analyze") as mock_gen:
            mock_gen.return_value = VisionResult(
                text="Camera frame showing an Arduino Mega board.",
                provider="Gemini",
                model="gemini-2.5-flash",
                image_count=1
            )
            files = [("file", ("frame.jpg", FRAME_ARDUINO_BOARD, "image/jpeg"))]
            data = {"session_id": "api_test_sess", "prompt": "What is this?"}
            r_frame = client.post("/api/vision/camera/session/frame", data=data, files=files)
            self.assertEqual(r_frame.status_code, 200, r_frame.text)
            self.assertEqual(r_frame.json()["status"], "success")

        # 4. End Session
        r_end = client.post("/api/vision/camera/session/end", data={"session_id": "api_test_sess"})
        self.assertEqual(r_end.status_code, 200)

        # Verify status 404 after purging
        r_stat_after = client.get("/api/vision/camera/session/status?session_id=api_test_sess")
        self.assertEqual(r_stat_after.status_code, 404)


if __name__ == "__main__":
    unittest.main()
