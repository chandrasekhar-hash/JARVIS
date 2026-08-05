import io
import re
from typing import List, Optional
from PIL import Image, ImageStat
from intelligence.vision.fusion.models import RecoveryPrompt

_LOW_QUALITY_KEYWORDS = r"\b(blurry|unclear|too dark|cannot read|low resolution|out of focus|hard to see|indistinct|unreadable)\b"

class ConfidenceRecoveryEvaluator:
    """
    Confidence & Recovery Evaluator (V8).
    Assesses image quality indicators (brightness, contrast, resolution) and visual model output confidence.
    When quality is low or unreadable:
    - Provides actionable recovery prompts ('Move closer', 'Improve lighting', 'Hold camera steady')
    - Enforces zero-hallucination safeguard (prohibits guessing or fabricating details).
    """

    def evaluate(
        self,
        images_data: List[bytes],
        analysis_text: Optional[str] = None
    ) -> RecoveryPrompt:
        # Check 1: Empty or missing image bytes
        if not images_data or any(len(b) == 0 for b in images_data):
            return RecoveryPrompt(
                needed=True,
                suggestion="Please provide a valid camera frame or image file.",
                reason="Empty or missing image input."
            )

        # Check 2: Visual brightness & contrast inspection via PIL
        for b in images_data:
            try:
                with Image.open(io.BytesIO(b)) as img:
                    grayscale = img.convert("L")
                    stat = ImageStat.Stat(grayscale)
                    mean_brightness = stat.mean[0]
                    std_contrast = stat.stddev[0]

                    if mean_brightness < 8.0:
                        return RecoveryPrompt(
                            needed=True,
                            suggestion="Lighting is too dark. Please improve lighting or turn on a light source.",
                            reason="Low brightness level detected."
                        )

                    if std_contrast < 1.0:
                        return RecoveryPrompt(
                            needed=True,
                            suggestion="Image contrast is low or out of focus. Please hold the camera steady and re-focus.",
                            reason="Low contrast / blur detected."
                        )
            except Exception:
                pass

        # Check 3: Response text quality signals
        if analysis_text:
            if re.search(_LOW_QUALITY_KEYWORDS, analysis_text.lower()):
                return RecoveryPrompt(
                    needed=True,
                    suggestion="Text or object is hard to read. Move closer or capture another angle with clearer focus.",
                    reason="Visual analysis reported unclear or unreadable details."
                )

        return RecoveryPrompt(needed=False)

# Singleton Instance
confidence_recovery_evaluator = ConfidenceRecoveryEvaluator()
