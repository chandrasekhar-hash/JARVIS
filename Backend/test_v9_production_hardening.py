import sys
import os
import io
import time
import unittest
from unittest.mock import patch, MagicMock
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app
from intelligence.vision.camera.session_manager import session_manager
from intelligence.vision.fusion.context_builder import context_builder

client = TestClient(app)

class TestV9ProductionHardening(unittest.TestCase):

    def setUp(self):
        session_manager.sessions.clear()
        context_builder.contexts.clear()

    # --- 1. SECURITY & INPUT VALIDATION TESTS ---
    def test_empty_file_upload_returns_400(self):
        files = [("images", ("empty.png", b"", "image/png"))]
        response = client.post("/api/vision/analyze", files=files)
        self.assertEqual(response.status_code, 400)
        self.assertIn("empty", response.json()["detail"].lower())

    def test_oversized_file_upload_returns_413(self):
        # Generate 11MB dummy payload
        big_bytes = b"0" * (11 * 1024 * 1024)
        files = [("images", ("big.png", big_bytes, "image/png"))]
        response = client.post("/api/vision/analyze", files=files)
        self.assertEqual(response.status_code, 413)

    # --- 2. OBSERVABILITY & HEALTH ENDPOINTS ---
    def test_health_and_diagnostics_endpoints(self):
        r_health = client.get("/api/health")
        self.assertEqual(r_health.status_code, 200)
        self.assertEqual(r_health.json().get("status"), "healthy")

        r_diag = client.get("/api/diagnostics/system")
        self.assertEqual(r_diag.status_code, 200)
        res_diag = r_diag.json()
        self.assertIn("system", res_diag)
        self.assertIn("cpu_percent", res_diag["system"])

    # --- 3. MEMORY LEAK & CLEANUP AUDIT ---
    def test_ephemeral_session_memory_leak_free(self):
        # Create and terminate 20 sessions rapidly
        for i in range(20):
            sid = f"hardening_sess_{i}"
            session_manager.get_or_create_session(sid)
            session_manager.purge_session(sid)

        self.assertEqual(len(session_manager.sessions), 0)

    # --- 4. RELIABILITY & ERROR MASKING ---
    @patch("intelligence.vision.providers.gemini_vision.GeminiVisionProvider.analyze")
    def test_gemini_quota_error_degradation_without_crash(self, mock_gen):
        mock_gen.side_effect = Exception("429 Quota exceeded for metric")
        img = Image.new("RGB", (64, 64), color=(50, 100, 150))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        files = [("images", ("test.png", png_bytes, "image/png"))]
        
        response = client.post("/api/vision/analyze", data={"prompt": "test"}, files=files)
        self.assertEqual(response.status_code, 500)
        # Verify stack trace is masked in production detail response
        self.assertNotIn("Traceback", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
