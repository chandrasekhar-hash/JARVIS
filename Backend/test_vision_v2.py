import sys
import os
import io
import unittest
from unittest.mock import patch, MagicMock
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app
from intelligence.vision.models import VisionRequest, VisionImageItem, VisionResult
from intelligence.vision.vision_service import vision_service, MAX_IMAGE_SIZE_BYTES

client = TestClient(app)

def create_dummy_image_bytes(format_name="PNG", width=50, height=50, color=(0, 255, 102)):
    """Helper function to generate valid image bytes for testing."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format=format_name)
    return buf.getvalue()

class TestVisionV2ServiceAndAPI(unittest.TestCase):

    def test_valid_png_validation(self):
        png_bytes = create_dummy_image_bytes("PNG")
        mime = vision_service.validate_image_bytes(png_bytes, "test.png", "image/png")
        self.assertEqual(mime, "image/png")

    def test_valid_jpeg_validation(self):
        jpg_bytes = create_dummy_image_bytes("JPEG")
        mime = vision_service.validate_image_bytes(jpg_bytes, "test.jpg", "image/jpeg")
        self.assertEqual(mime, "image/jpeg")

    def test_valid_webp_validation(self):
        webp_bytes = create_dummy_image_bytes("WEBP")
        mime = vision_service.validate_image_bytes(webp_bytes, "test.webp", "image/webp")
        self.assertEqual(mime, "image/webp")

    def test_zero_byte_image_rejection(self):
        with self.assertRaises(ValueError) as ctx:
            vision_service.validate_image_bytes(b"", "empty.png", "image/png")
        self.assertIn("empty (0 bytes)", str(ctx.exception))

    def test_corrupted_image_rejection(self):
        corrupted_bytes = b"NOT_A_REAL_IMAGE_HEADER_BYTES_12345"
        with self.assertRaises(ValueError) as ctx:
            vision_service.validate_image_bytes(corrupted_bytes, "fake.jpg", "image/jpeg")
        self.assertIn("corrupted or is not a valid image", str(ctx.exception))

    def test_fake_jpg_renamed_exe_rejection(self):
        fake_exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
        with self.assertRaises(ValueError) as ctx:
            vision_service.validate_image_bytes(fake_exe_bytes, "virus.jpg", "image/jpeg")
        self.assertIn("corrupted or is not a valid image", str(ctx.exception))

    def test_oversized_image_rejection(self):
        oversized_bytes = b"A" * (MAX_IMAGE_SIZE_BYTES + 1024)
        with self.assertRaises(ValueError) as ctx:
            vision_service.validate_image_bytes(oversized_bytes, "huge.png", "image/png")
        self.assertIn("exceeds maximum allowed limit", str(ctx.exception))

    def test_more_than_max_images_rejection(self):
        png_bytes = create_dummy_image_bytes("PNG")
        items = [
            VisionImageItem(filename=f"img_{i}.png", content_type="image/png", data=png_bytes, size=len(png_bytes))
            for i in range(6) # 6 images > max 5
        ]
        req = VisionRequest(prompt="Test", images=items)

        # Run async in event loop
        import asyncio
        with self.assertRaises(ValueError) as ctx:
            asyncio.run(vision_service.analyze_images(req))
        self.assertIn("Maximum 5 images allowed", str(ctx.exception))

    @patch("intelligence.vision.providers.gemini_vision.GeminiVisionProvider.analyze")
    def test_api_endpoint_valid_image_and_prompt(self, mock_analyze):
        mock_analyze.return_value = VisionResult(
            text="This is a test image of a green square.",
            provider="Gemini",
            model="gemini-2.5-flash",
            image_count=1
        )

        png_bytes = create_dummy_image_bytes("PNG")
        files = [("images", ("test.png", png_bytes, "image/png"))]
        data = {"prompt": "What color is this square?"}

        response = client.post("/api/vision/analyze", data=data, files=files)
        self.assertEqual(response.status_code, 200, response.text)
        res_json = response.json()
        self.assertEqual(res_json["status"], "success")
        self.assertEqual(res_json["text"], "This is a test image of a green square.")
        self.assertEqual(res_json["image_count"], 1)

    @patch("intelligence.vision.providers.gemini_vision.GeminiVisionProvider.analyze")
    def test_api_endpoint_image_only_no_prompt(self, mock_analyze):
        mock_analyze.return_value = VisionResult(
            text="Automatic description of the uploaded image.",
            provider="Gemini",
            model="gemini-2.5-flash",
            image_count=1
        )

        jpg_bytes = create_dummy_image_bytes("JPEG")
        files = [("images", ("test.jpg", jpg_bytes, "image/jpeg"))]

        response = client.post("/api/vision/analyze", files=files)
        self.assertEqual(response.status_code, 200, response.text)
        res_json = response.json()
        self.assertEqual(res_json["status"], "success")
        self.assertEqual(res_json["text"], "Automatic description of the uploaded image.")

    @patch("intelligence.vision.providers.gemini_vision.GeminiVisionProvider.analyze")
    def test_api_endpoint_multiple_images(self, mock_analyze):
        mock_analyze.return_value = VisionResult(
            text="Comparison of Image 1 and Image 2: both are valid test squares.",
            provider="Gemini",
            model="gemini-2.5-flash",
            image_count=2
        )

        img1 = create_dummy_image_bytes("PNG", color=(0, 255, 102))
        img2 = create_dummy_image_bytes("JPEG", color=(255, 0, 102))
        files = [
            ("images", ("img1.png", img1, "image/png")),
            ("images", ("img2.jpg", img2, "image/jpeg"))
        ]
        data = {"prompt": "Compare these two images."}

        response = client.post("/api/vision/analyze", data=data, files=files)
        self.assertEqual(response.status_code, 200, response.text)
        res_json = response.json()
        self.assertEqual(res_json["image_count"], 2)

    def test_api_endpoint_corrupted_file_rejection(self):
        corrupted_bytes = b"FAKEDATA_NOT_A_REAL_IMAGE"
        files = [("images", ("corrupted.jpg", corrupted_bytes, "image/jpeg"))]

        response = client.post("/api/vision/analyze", files=files)
        self.assertEqual(response.status_code, 400)
        self.assertIn("corrupted or is not a valid image", response.json()["detail"])

if __name__ == "__main__":
    unittest.main()
