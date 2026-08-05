import sys
import os
import io
import unittest
from unittest.mock import patch, MagicMock
from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app
from intelligence.vision.models import VisionRequest, VisionImageItem, VisionResult
from intelligence.vision.ocr.models import OCRRequest, OCRResult, OCRImageResult
from intelligence.vision.ocr.ocr_service import ocr_service
from intelligence.vision.ocr.providers.gemini_ocr import GeminiOCRProvider
from intelligence.vision.task_classifier import classify_visual_task, VisualTask

client = TestClient(app)

def create_text_image(text: str, width=400, height=200, bg_color=(255, 255, 255), text_color=(0, 0, 0)):
    """Helper function to generate clean test images with text."""
    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), text, fill=text_color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def calculate_cer(reference: str, hypothesis: str) -> float:
    """Calculates Character Error Rate (CER) between ground truth reference and hypothesis."""
    ref = reference.strip()
    hyp = hypothesis.strip()
    if not ref:
        return 0.0 if not hyp else 1.0
    
    # Levenshtein distance on characters
    d = [[0] * (len(hyp) + 1) for _ in range(len(ref) + 1)]
    for i in range(len(ref) + 1):
        d[i][0] = i
    for j in range(len(hyp) + 1):
        d[0][j] = j

    for i in range(1, len(ref) + 1):
        for j in range(1, len(hyp) + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            d[i][j] = min(
                d[i - 1][j] + 1,      # deletion
                d[i][j - 1] + 1,      # insertion
                d[i - 1][j - 1] + cost # substitution
            )

    edits = d[len(ref)][len(hyp)]
    return edits / float(len(ref))

class TestVisionV4OCRDedicatedIntelligence(unittest.TestCase):

    # --- 1. OCR TASK CLASSIFICATION & ROUTING ---
    def test_task_classifier_pure_extraction(self):
        self.assertEqual(classify_visual_task("Extract the text"), VisualTask.TEXT_EXTRACTION)
        self.assertEqual(classify_visual_task("Copy all text from this screenshot"), VisualTask.TEXT_EXTRACTION)
        self.assertEqual(classify_visual_task("Transcribe this image"), VisualTask.TEXT_EXTRACTION)
        self.assertEqual(classify_visual_task("Get the exact error message"), VisualTask.TEXT_EXTRACTION)

    def test_task_classifier_extraction_and_reasoning(self):
        self.assertEqual(classify_visual_task("Extract this error and explain it"), VisualTask.EXTRACTION_REASONING)
        self.assertEqual(classify_visual_task("Read this text and tell me why it failed"), VisualTask.EXTRACTION_REASONING)

    # --- 2. NO-TEXT DETECTION & STRUCTURE ---
    def test_no_text_parsing_structure(self):
        provider = GeminiOCRProvider()
        raw = "[IMAGE 1]\n[NO_READABLE_TEXT]"
        comb, has_txt, items = provider._parse_ocr_response(raw, 1)

        self.assertFalse(has_txt)
        self.assertIn("No readable text was detected", comb)
        self.assertEqual(len(items), 1)
        self.assertFalse(items[0].has_text)

    def test_multi_image_ocr_parsing_structure(self):
        provider = GeminiOCRProvider()
        raw = "[IMAGE 1]\nALPHA\n\n[IMAGE 2]\nBETA"
        comb, has_txt, items = provider._parse_ocr_response(raw, 2)

        self.assertTrue(has_txt)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].text, "ALPHA")
        self.assertEqual(items[1].text, "BETA")
        self.assertIn("--- Image 1 ---", comb)
        self.assertIn("--- Image 2 ---", comb)

    # --- 3. CER ACCURACY CALCULATION HELPER ---
    def test_cer_calculation_exact(self):
        ref = "JARVIS VISION HELLO WORLD"
        hyp = "JARVIS VISION HELLO WORLD"
        cer = calculate_cer(ref, hyp)
        self.assertEqual(cer, 0.0)

    def test_cer_calculation_with_substitutions(self):
        ref = "HELLO"
        hyp = "HELL0" # 1 substitution
        cer = calculate_cer(ref, hyp)
        self.assertAlmostEqual(cer, 0.2)

    # --- 4. EXIF PREPROCESSING ---
    def test_exif_preprocessing_transpose(self):
        # Create small valid PNG bytes
        img_bytes = create_text_image("EXIF TEST")
        processed = ocr_service.process_exif_orientation(img_bytes)
        self.assertTrue(len(processed) > 0)

    # --- 5. DEDICATED POST /api/vision/ocr ENDPOINT ---
    @patch("intelligence.vision.ocr.ocr_service.OCRService.extract")
    def test_api_vision_ocr_endpoint(self, mock_extract):
        mock_extract.return_value = OCRResult(
            text="JARVIS VISION 2026",
            has_text=True,
            image_count=1,
            images=[OCRImageResult(index=1, text="JARVIS VISION 2026", has_text=True)],
            provider="Gemini",
            model="gemini-2.5-flash"
        )

        img_bytes = create_text_image("JARVIS VISION 2026")
        files = [("images", ("test.png", img_bytes, "image/png"))]
        data = {"language_hint": "en"}

        response = client.post("/api/vision/ocr", data=data, files=files)
        self.assertEqual(response.status_code, 200, response.text)
        res = response.json()

        self.assertEqual(res["status"], "success")
        self.assertTrue(res["has_text"])
        self.assertEqual(res["text"], "JARVIS VISION 2026")
        self.assertEqual(len(res["images"]), 1)

    # --- 6. UNIFIED ROUTING INTEGRATION ---
    @patch("intelligence.vision.ocr.ocr_service.OCRService.extract")
    def test_unified_analyze_routing_pure_ocr(self, mock_extract):
        mock_extract.return_value = OCRResult(
            text="Extracted error code 404",
            has_text=True,
            image_count=1,
            images=[OCRImageResult(index=1, text="Extracted error code 404", has_text=True)],
            provider="Gemini",
            model="gemini-2.5-flash"
        )

        img_bytes = create_text_image("Extracted error code 404")
        files = [("images", ("err.png", img_bytes, "image/png"))]
        data = {"prompt": "Extract the exact error message"}

        response = client.post("/api/vision/analyze", data=data, files=files)
        self.assertEqual(response.status_code, 200, response.text)
        res = response.json()

        self.assertEqual(res["status"], "success")
        self.assertEqual(res["task_type"], "TEXT_EXTRACTION")
        self.assertEqual(res["text"], "Extracted error code 404")
        self.assertEqual(res["metadata"]["provider_calls"], 1)

if __name__ == "__main__":
    unittest.main()
