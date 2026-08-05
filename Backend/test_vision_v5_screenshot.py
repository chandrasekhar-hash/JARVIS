import sys
import os
import io
import unittest
from unittest.mock import patch, MagicMock
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app
from intelligence.vision.task_classifier import classify_visual_task, VisualTask
from intelligence.vision.screenshot.screen_type_detector import (
    ScreenTypeDetector, ScreenCategory, ApplicationHint, screen_type_detector
)
from intelligence.vision.screenshot.screenshot_instructions import get_screenshot_instruction
from intelligence.vision.instruction_builder import build_vision_instruction
from intelligence.vision.models import VisionResult

client = TestClient(app)

# ---------------------------------------------------------------------------
# Image fixture helpers
# ---------------------------------------------------------------------------

def _make_png(label: str, width=640, height=480, bg=(30, 30, 30), fg=(220, 220, 220)) -> bytes:
    """Creates a synthetic screenshot fixture as PNG bytes."""
    img = Image.new("RGB", (width, height), color=bg)
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), label, fill=fg)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# Synthetic screenshot fixtures
FIXTURE_VSCODE = _make_png("VS Code\nExplorer | main.py\n12: import requests  ← red underline")
FIXTURE_PYCHARM = _make_png("PyCharm\nProject: myapp | run config: main")
FIXTURE_TERMINAL_TRACEBACK = _make_png("$ python app.py\nTraceback (most recent call last):\n  File 'app.py', line 7\nModuleNotFoundError: No module named 'requests'")
FIXTURE_TERMINAL_DOCKER = _make_png("$ docker compose up\nCreating container myapp ... error\nERR: port 8080 already in use")
FIXTURE_TERMINAL_NPM = _make_png("$ npm install\nnpm ERR! peer dep missing: react@18")
FIXTURE_BROWSER_404 = _make_png("Chrome\n404 Not Found\nhttps://example.com/api/user")
FIXTURE_BROWSER_REACT = _make_png("React App\nChrome | localhost:3000\nBlank white page")
FIXTURE_DEVTOOLS_CONSOLE = _make_png("Chrome DevTools > Console\nUncaught TypeError: Cannot read properties of undefined\napp.js:42")
FIXTURE_DEVTOOLS_NETWORK = _make_png("Chrome DevTools > Network\nPOST /api/login  401 Unauthorized  120ms\nCORS error on GET /api/data")
FIXTURE_GITHUB_PR = _make_png("GitHub\nfeature/ocr-v4 → main\nCI: 3 checks passed ✓\nRequested reviewer: @johndoe")
FIXTURE_DOCKER = _make_png("Docker Desktop\nmyapp-web: running (healthy)\nmyapp-db: exited (1)")
FIXTURE_DASHBOARD = _make_png("Analytics Dashboard\nDAU: 12,450 (+8%)\nRevenue: $45,200\nError Rate: 0.2%")
FIXTURE_FIGMA = _make_png("Figma\nDesign: Onboarding v3\nLayer: Button/Primary/Hover")
FIXTURE_FIREBASE = _make_png("Firebase Console\nFirestore > users > uid_123\ncreatedAt: 2026-01-01")
FIXTURE_SUPABASE = _make_png("Supabase\nTable Editor > profiles\nRLS: enabled, 3 policies")
FIXTURE_MACOS_SETTINGS = _make_png("macOS System Settings\nPrivacy & Security > Camera\nAllow: VS Code [toggle ON]")
FIXTURE_ANDROID_SETTINGS = _make_png("Android Settings\nApps > JARVIS > Permissions\nMicrophone: Allowed")
FIXTURE_IPHONE = _make_png("iPhone Settings\nNotifications > JARVIS\nAllow Notifications: ON")
FIXTURE_GIT = _make_png("$ git status\nOn branch main\nYour branch is ahead of origin by 2 commits")
FIXTURE_FASTAPI = _make_png("FastAPI /docs\nPOST /api/vision/analyze\nResponse: 200 OK")


class TestV5ScreenshotTaskClassification(unittest.TestCase):
    """Tests that SCREENSHOT task enum fires correctly for screenshot-signaled prompts."""

    def test_vscode_prompt_classifies_screenshot(self):
        self.assertEqual(classify_visual_task("What error is in VS Code?"), VisualTask.SCREENSHOT)

    def test_cursor_editor_prompt(self):
        self.assertEqual(classify_visual_task("Why is Cursor editor showing this warning?"), VisualTask.SCREENSHOT)

    def test_pycharm_prompt(self):
        self.assertEqual(classify_visual_task("What does PyCharm say is wrong?"), VisualTask.SCREENSHOT)

    def test_terminal_prompt(self):
        self.assertEqual(classify_visual_task("What is this terminal output?"), VisualTask.SCREENSHOT)

    def test_docker_prompt(self):
        self.assertEqual(classify_visual_task("Why is Docker failing?"), VisualTask.SCREENSHOT)

    def test_github_pr_prompt(self):
        self.assertEqual(classify_visual_task("What is the GitHub PR status?"), VisualTask.SCREENSHOT)

    def test_devtools_prompt(self):
        self.assertEqual(classify_visual_task("Explain this Chrome DevTools console error"), VisualTask.SCREENSHOT)

    def test_figma_prompt(self):
        self.assertEqual(classify_visual_task("What layer is selected in Figma?"), VisualTask.SCREENSHOT)

    def test_firebase_prompt(self):
        self.assertEqual(classify_visual_task("What does the Firebase console show?"), VisualTask.SCREENSHOT)

    def test_iphone_settings_prompt(self):
        self.assertEqual(classify_visual_task("Where is this setting on iPhone?"), VisualTask.SCREENSHOT)

    def test_dashboard_prompt(self):
        self.assertEqual(classify_visual_task("Explain this analytics dashboard"), VisualTask.SCREENSHOT)

    def test_generic_screenshot_prompt(self):
        self.assertEqual(classify_visual_task("What is showing on this screenshot?"), VisualTask.SCREENSHOT)

    def test_ide_prompt(self):
        self.assertEqual(classify_visual_task("Explain this IDE error"), VisualTask.SCREENSHOT)

    # --- Existing task types must NOT regress to SCREENSHOT ---
    def test_no_screenshot_for_empty_prompt(self):
        self.assertEqual(classify_visual_task(""), VisualTask.GENERAL_DESCRIPTION)

    def test_no_screenshot_for_extraction_prompt(self):
        # OCR extraction takes priority over screenshot signals
        result = classify_visual_task("Extract all text from this screenshot")
        self.assertEqual(result, VisualTask.TEXT_EXTRACTION)

    def test_no_screenshot_for_chart_prompt(self):
        result = classify_visual_task("What does this chart show?")
        self.assertIn(result, [VisualTask.CHART_ANALYSIS, VisualTask.TARGETED_QUESTION, VisualTask.GENERAL_DESCRIPTION])

    def test_comparison_overrides_screenshot_for_multi_image(self):
        result = classify_visual_task("Compare these two", image_count=2)
        self.assertEqual(result, VisualTask.IMAGE_COMPARISON)


class TestV5ScreenTypeDetector(unittest.TestCase):
    """Tests that ScreenTypeDetector resolves correct category + app hint."""

    def setUp(self):
        self.detector = ScreenTypeDetector()

    def test_vscode_detection(self):
        ctx = self.detector.detect("What is wrong in VS Code?")
        self.assertEqual(ctx.category, ScreenCategory.IDE)
        self.assertEqual(ctx.app_hint, ApplicationHint.VSCODE)

    def test_cursor_detection(self):
        ctx = self.detector.detect("cursor editor is showing this")
        self.assertEqual(ctx.category, ScreenCategory.IDE)
        self.assertEqual(ctx.app_hint, ApplicationHint.CURSOR)

    def test_pycharm_detection(self):
        ctx = self.detector.detect("PyCharm shows a red underline")
        self.assertEqual(ctx.category, ScreenCategory.IDE)
        self.assertEqual(ctx.app_hint, ApplicationHint.PYCHARM)

    def test_terminal_detection(self):
        ctx = self.detector.detect("terminal output shows ModuleNotFoundError")
        self.assertEqual(ctx.category, ScreenCategory.TERMINAL)

    def test_devtools_console_detection(self):
        ctx = self.detector.detect("what does this chrome devtools console tab show?")
        self.assertEqual(ctx.category, ScreenCategory.DEVTOOLS)

    def test_network_tab_detection(self):
        ctx = self.detector.detect("Why is the network tab showing a 401?")
        self.assertEqual(ctx.category, ScreenCategory.DEVTOOLS)

    def test_github_detection(self):
        ctx = self.detector.detect("What is the GitHub PR status?")
        self.assertEqual(ctx.category, ScreenCategory.DEVELOPER_TOOL)
        self.assertEqual(ctx.app_hint, ApplicationHint.GITHUB)

    def test_docker_detection(self):
        ctx = self.detector.detect("Docker container is exited")
        self.assertEqual(ctx.category, ScreenCategory.DEVELOPER_TOOL)
        self.assertEqual(ctx.app_hint, ApplicationHint.DOCKER)

    def test_npm_detection(self):
        ctx = self.detector.detect("npm install failed")
        self.assertEqual(ctx.category, ScreenCategory.DEVELOPER_TOOL)
        self.assertEqual(ctx.app_hint, ApplicationHint.NPM)

    def test_firebase_detection(self):
        ctx = self.detector.detect("Firebase console shows this document")
        self.assertEqual(ctx.category, ScreenCategory.DATABASE_TOOL)
        self.assertEqual(ctx.app_hint, ApplicationHint.FIREBASE)

    def test_supabase_detection(self):
        ctx = self.detector.detect("Supabase table editor is showing this")
        self.assertEqual(ctx.category, ScreenCategory.DATABASE_TOOL)
        self.assertEqual(ctx.app_hint, ApplicationHint.SUPABASE)

    def test_figma_detection(self):
        ctx = self.detector.detect("What layer is this in Figma?")
        self.assertEqual(ctx.category, ScreenCategory.DESIGN_TOOL)
        self.assertEqual(ctx.app_hint, ApplicationHint.FIGMA)

    def test_dashboard_detection(self):
        ctx = self.detector.detect("Explain this analytics dashboard")
        self.assertEqual(ctx.category, ScreenCategory.DASHBOARD)

    def test_macos_settings_detection(self):
        ctx = self.detector.detect("macOS system settings screen")
        self.assertEqual(ctx.category, ScreenCategory.SETTINGS)

    def test_iphone_detection(self):
        ctx = self.detector.detect("iPhone settings page")
        self.assertEqual(ctx.category, ScreenCategory.MOBILE)
        self.assertEqual(ctx.app_hint, ApplicationHint.IOS)

    def test_android_detection(self):
        ctx = self.detector.detect("Android settings screen")
        self.assertEqual(ctx.category, ScreenCategory.MOBILE)
        self.assertEqual(ctx.app_hint, ApplicationHint.ANDROID)

    def test_error_signal_detected(self):
        ctx = self.detector.detect("What is the traceback in VS Code?")
        self.assertTrue(ctx.has_error)

    def test_multi_panel_signal_detected(self):
        ctx = self.detector.detect("VS Code and the terminal both show errors")
        self.assertTrue(ctx.has_multi_panel)

    def test_unknown_prompt_returns_general(self):
        ctx = self.detector.detect("this random thing")
        self.assertEqual(ctx.category, ScreenCategory.GENERAL)

    def test_none_prompt_returns_general(self):
        ctx = self.detector.detect(None)
        self.assertEqual(ctx.category, ScreenCategory.GENERAL)


class TestV5InstructionBuilderScreenshot(unittest.TestCase):
    """Tests that build_vision_instruction returns screenshot-specific content."""

    def test_screenshot_task_builds_ide_instruction_for_vscode(self):
        with patch("intelligence.vision.screenshot.screen_type_detector.screen_type_detector.detect") as mock_detect:
            from intelligence.vision.screenshot.screen_type_detector import ScreenContext
            mock_detect.return_value = ScreenContext(
                category=ScreenCategory.IDE,
                app_hint=ApplicationHint.VSCODE,
                description="IDE / vscode"
            )
            instruction = build_vision_instruction(VisualTask.SCREENSHOT, "What error in VS Code?")
            self.assertIn("IDE", instruction)
            self.assertIn("VS Code", instruction)
            self.assertIn("VISIBLE EVIDENCE", instruction)

    def test_screenshot_task_builds_terminal_instruction(self):
        with patch("intelligence.vision.screenshot.screen_type_detector.screen_type_detector.detect") as mock_detect:
            from intelligence.vision.screenshot.screen_type_detector import ScreenContext
            mock_detect.return_value = ScreenContext(
                category=ScreenCategory.TERMINAL,
                app_hint=ApplicationHint.UNKNOWN,
                description="TERMINAL"
            )
            instruction = build_vision_instruction(VisualTask.SCREENSHOT, "What does this terminal output mean?")
            self.assertIn("TERMINAL", instruction)
            self.assertIn("STACK TRACE", instruction)

    def test_screenshot_task_builds_devtools_instruction(self):
        with patch("intelligence.vision.screenshot.screen_type_detector.screen_type_detector.detect") as mock_detect:
            from intelligence.vision.screenshot.screen_type_detector import ScreenContext
            mock_detect.return_value = ScreenContext(
                category=ScreenCategory.DEVTOOLS,
                app_hint=ApplicationHint.CHROME,
                description="DEVTOOLS / chrome"
            )
            instruction = build_vision_instruction(VisualTask.SCREENSHOT, "Network tab failure")
            self.assertIn("DEVELOPER TOOLS", instruction.upper())
            self.assertIn("NETWORK TAB", instruction.upper())

    def test_non_screenshot_tasks_unchanged(self):
        """V3/V4 tasks must continue to use original guidance — not screenshot templates."""
        instruction = build_vision_instruction(VisualTask.CHART_ANALYSIS)
        self.assertIn("CHART", instruction.upper())
        # These strings only appear in screenshot domain templates
        self.assertNotIn("CODE EDITOR", instruction)
        self.assertNotIn("SHELL OUTPUT", instruction)
        self.assertNotIn("DEVELOPER TOOLS", instruction)
        self.assertNotIn("ADMIN PANEL", instruction)


    def test_ui_analysis_unchanged(self):
        instruction = build_vision_instruction(VisualTask.UI_ANALYSIS)
        self.assertIn("UI", instruction.upper())


class TestV5APIEndpointIntegration(unittest.TestCase):
    """Integration tests: POST /api/vision/analyze returns SCREENSHOT task_type for screenshot prompts."""

    @patch("intelligence.vision.providers.gemini_vision.GeminiVisionProvider.analyze")
    def test_vscode_prompt_returns_screenshot_task(self, mock_analyze):
        mock_analyze.return_value = VisionResult(
            text="VS Code shows a red underline on line 12 — missing import.",
            provider="Gemini",
            model="gemini-2.5-flash",
            image_count=1,
            task_type=VisualTask.SCREENSHOT.value,
            visual_summary="VS Code editor with red underline on import statement.",
            metadata={}
        )

        response = client.post(
            "/api/vision/analyze",
            data={"prompt": "What error is showing in VS Code?"},
            files=[("images", ("vscode.png", FIXTURE_VSCODE, "image/png"))]
        )
        self.assertEqual(response.status_code, 200, response.text)
        res = response.json()
        self.assertEqual(res["task_type"], "SCREENSHOT")

    @patch("intelligence.vision.providers.gemini_vision.GeminiVisionProvider.analyze")
    def test_terminal_traceback_prompt_returns_screenshot_task(self, mock_analyze):
        mock_analyze.return_value = VisionResult(
            text="ModuleNotFoundError: No module named 'requests'",
            provider="Gemini",
            model="gemini-2.5-flash",
            image_count=1,
            task_type=VisualTask.SCREENSHOT.value,
            visual_summary="Python terminal traceback — ModuleNotFoundError.",
            metadata={}
        )

        # Use a prompt that explicitly names the terminal to trigger SCREENSHOT
        response = client.post(
            "/api/vision/analyze",
            data={"prompt": "What is shown in this terminal output?"},
            files=[("images", ("term.png", FIXTURE_TERMINAL_TRACEBACK, "image/png"))]
        )
        self.assertEqual(response.status_code, 200)
        res = response.json()
        self.assertEqual(res["task_type"], "SCREENSHOT")

    @patch("intelligence.vision.providers.gemini_vision.GeminiVisionProvider.analyze")
    def test_dashboard_prompt_returns_screenshot_task(self, mock_analyze):
        mock_analyze.return_value = VisionResult(
            text="DAU: 12,450 (+8%), Revenue: $45,200, Error Rate: 0.2%",
            provider="Gemini",
            model="gemini-2.5-flash",
            image_count=1,
            task_type=VisualTask.SCREENSHOT.value,
            visual_summary="Analytics dashboard with KPI cards.",
            metadata={}
        )

        response = client.post(
            "/api/vision/analyze",
            data={"prompt": "Explain this analytics dashboard"},
            files=[("images", ("dash.png", FIXTURE_DASHBOARD, "image/png"))]
        )
        self.assertEqual(response.status_code, 200)
        res = response.json()
        self.assertEqual(res["task_type"], "SCREENSHOT")

    @patch("intelligence.vision.providers.gemini_vision.GeminiVisionProvider.analyze")
    def test_github_pr_prompt_returns_screenshot_task(self, mock_analyze):
        mock_analyze.return_value = VisionResult(
            text="PR is open with 3 CI checks passed.",
            provider="Gemini",
            model="gemini-2.5-flash",
            image_count=1,
            task_type=VisualTask.SCREENSHOT.value,
            visual_summary="GitHub PR page, 3 CI checks passing.",
            metadata={}
        )

        response = client.post(
            "/api/vision/analyze",
            data={"prompt": "What is the GitHub PR status?"},
            files=[("images", ("gh.png", FIXTURE_GITHUB_PR, "image/png"))]
        )
        self.assertEqual(response.status_code, 200)
        res = response.json()
        self.assertEqual(res["task_type"], "SCREENSHOT")


class TestV5Regressions(unittest.TestCase):
    """V5 must not affect V2/V3/V4 task routing."""

    def test_empty_prompt_general(self):
        self.assertEqual(classify_visual_task(""), VisualTask.GENERAL_DESCRIPTION)

    def test_text_extraction_not_screenshot(self):
        self.assertEqual(classify_visual_task("Extract the text"), VisualTask.TEXT_EXTRACTION)

    def test_extraction_reasoning_not_screenshot(self):
        self.assertEqual(classify_visual_task("Extract this error and explain it"), VisualTask.EXTRACTION_REASONING)

    def test_chart_analysis_not_screenshot(self):
        # "chart" does not contain any screenshot-specific app name
        result = classify_visual_task("What does this chart show?")
        self.assertNotEqual(result, VisualTask.SCREENSHOT)

    def test_multi_image_comparison_preserved(self):
        result = classify_visual_task("", image_count=2)
        self.assertEqual(result, VisualTask.IMAGE_COMPARISON)

    def test_troubleshooting_ambiguous_preserved(self):
        result = classify_visual_task("what's wrong?")
        self.assertEqual(result, VisualTask.VISUAL_TROUBLESHOOTING)


if __name__ == "__main__":
    unittest.main()
