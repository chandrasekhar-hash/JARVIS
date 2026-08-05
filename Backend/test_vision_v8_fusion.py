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
from intelligence.vision.models import VisionImageItem, VisionResult
from intelligence.vision.ocr.models import OCRResult, OCRImageResult
from intelligence.vision.fusion.models import CapabilityType, MultimodalContext
from intelligence.vision.fusion.context_builder import context_builder, MultimodalContextBuilder
from intelligence.vision.fusion.pronoun_resolver import pronoun_resolver, PronounResolver
from intelligence.vision.fusion.capability_router import capability_router, AutomaticCapabilityRouter
from intelligence.vision.fusion.clarification_engine import clarification_engine, ClarificationEngine
from intelligence.vision.fusion.confidence_recovery import confidence_recovery_evaluator, ConfidenceRecoveryEvaluator
from intelligence.vision.fusion.fusion_service import multimodal_fusion_service, MultimodalFusionService

client = TestClient(app)

def _make_test_png(text: str, width=640, height=480, bg=(30, 30, 35), fg=(220, 220, 225)) -> bytes:
    img = Image.new("RGB", (width, height), color=bg)
    draw = ImageDraw.Draw(img)
    lines = text.split("\n")
    y = 20
    for line in lines:
        draw.text((20, y), line, fill=fg)
        y += 25
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

IMG_NORMAL = _make_test_png("Normal Desk View\nLaptop and Coffee Cup")
IMG_RECEIPT = _make_test_png("RECEIPT #4991\nStore: Tech Hub\nItem: USB Cable\nTotal: $12.99")
IMG_DARK = _make_test_png("Dark View", bg=(5, 5, 5), fg=(15, 15, 15))


class TestVisionV8VoiceVisionFusion(unittest.TestCase):

    def setUp(self):
        context_builder.contexts.clear()

    # --- 1. PRONOUN RESOLUTION TESTS ---
    def test_pronoun_resolution_unambiguous(self):
        ctx = context_builder.get_or_create_context("sess_1")
        ctx.active_focus = "Arduino Mega board"

        res = pronoun_resolver.resolve_pronouns("What is connected to this?", ctx)
        self.assertFalse(res.is_ambiguous)
        self.assertIn("Arduino Mega board", res.resolved_text)
        self.assertEqual(res.target_object, "Arduino Mega board")

    def test_pronoun_resolution_ambiguous_never_guesses(self):
        ctx = context_builder.get_or_create_context("sess_2")
        ctx.active_focus = "Receipt #101"
        ctx.latest_ocr = {"text": "Bottle Label #402"}

        res = pronoun_resolver.resolve_pronouns("What does this say?", ctx, camera_focus="Receipt #101")
        self.assertTrue(res.is_ambiguous)
        self.assertGreaterEqual(len(res.ambiguity_candidates), 2)

    # --- 2. AUTOMATIC CAPABILITY ROUTER TESTS ---
    def test_auto_capability_selection_ocr(self):
        ctx = context_builder.get_or_create_context("sess_ocr")
        res = capability_router.route_capability(
            prompt="Read this receipt label",
            image_count=1,
            context=ctx
        )
        self.assertEqual(res.selected_capability, CapabilityType.OCR)

    def test_auto_capability_selection_multi_image(self):
        ctx = context_builder.get_or_create_context("sess_multi")
        res = capability_router.route_capability(
            prompt="Compare these two items",
            image_count=2,
            context=ctx
        )
        self.assertEqual(res.selected_capability, CapabilityType.MULTI_IMAGE)

    def test_auto_capability_selection_screenshot(self):
        ctx = context_builder.get_or_create_context("sess_shot")
        res = capability_router.route_capability(
            prompt="What is the error in VS Code terminal?",
            image_count=1,
            context=ctx,
            attachment_metadata=[{"filename": "screenshot_1.png", "size": 1024}]
        )
        self.assertEqual(res.selected_capability, CapabilityType.SCREENSHOT)

    # --- 3. CLARIFICATION ENGINE TESTS ---
    def test_clarification_engine_prompts_on_ambiguity(self):
        ctx = context_builder.get_or_create_context("sess_clar")
        pronoun_res = pronoun_resolver.resolve_pronouns(
            "Read this",
            ctx,
            camera_focus="Receipt"
        )
        # Manually force ambiguity for test validation
        pronoun_res.is_ambiguous = True
        pronoun_res.ambiguity_candidates = ["bottle label", "receipt #101"]

        clar_res = clarification_engine.evaluate_clarification(pronoun_res, "Read this", ctx)
        self.assertTrue(clar_res.is_ambiguous)
        self.assertIn("Do you mean", clar_res.question)

    # --- 4. CONFIDENCE & RECOVERY TESTS ---
    def test_confidence_recovery_evaluator_dark_image(self):
        rec_prompt = confidence_recovery_evaluator.evaluate([IMG_DARK], "Sample response")
        self.assertTrue(rec_prompt.needed)
        self.assertIn("Lighting is too dark", rec_prompt.suggestion)

    # --- 5. EPHEMERAL CONTEXT EXPIRATION ---
    def test_context_expiration(self):
        ctx = context_builder.get_or_create_context("stale_sess")
        ctx.last_updated_at = time.time() - 400 # 400s > 300s timeout

        context_builder.cleanup_expired_contexts(timeout_seconds=300)
        self.assertNotIn("stale_sess", context_builder.contexts)

    # --- 6. END-TO-END MULTIMODAL FUSION SERVICE ---
    @patch("intelligence.vision.providers.gemini_vision.GeminiVisionProvider.analyze")
    def test_fusion_service_end_to_end_vision(self, mock_gen):
        mock_gen.return_value = VisionResult(
            text="The image shows a laptop on a desk next to a coffee mug.",
            provider="Gemini",
            model="gemini-2.5-flash",
            image_count=1,
            visual_summary="Laptop and coffee mug on desk."
        )

        import asyncio
        img_item = VisionImageItem(filename="desk.png", content_type="image/png", data=IMG_NORMAL, size=len(IMG_NORMAL))
        res = asyncio.run(multimodal_fusion_service.process_multimodal_request(
            prompt="Describe this scene",
            image_items=[img_item],
            session_id="fusion_e2e_sess"
        ))

        self.assertEqual(res.capability_used, CapabilityType.VISION)
        self.assertIn("laptop", res.text.lower())
        self.assertIsNotNone(context_builder.contexts.get("fusion_e2e_sess"))


if __name__ == "__main__":
    unittest.main()
