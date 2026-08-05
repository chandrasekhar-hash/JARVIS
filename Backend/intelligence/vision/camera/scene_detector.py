import io
import time
from typing import Optional
from PIL import Image

from intelligence.vision.camera.models import SceneChangeResult

class SceneChangeDetector:
    """
    Scene Change Detector (V7).
    Lightweight, fast visual change detector (< 5ms execution latency).
    Answers strictly: 'Should this frame be analyzed?'
    Does NOT perform semantic change reasoning (delegated to MultiImage Intelligence V6).
    """

    def __init__(self, threshold: float = 0.05, dhash_threshold: int = 6):
        self.threshold = threshold
        self.dhash_threshold = dhash_threshold

    def compute_dhash(self, img: Image.Image) -> str:
        """
        Computes 32x32 difference hash (dHash) string.
        """
        resized = img.convert("L").resize((33, 32), Image.Resampling.BILINEAR)
        pixels = list(resized.get_flattened_data() if hasattr(resized, "get_flattened_data") else resized.getdata())
        bits = []
        for row in range(32):
            for col in range(32):
                p1 = pixels[row * 33 + col]
                p2 = pixels[row * 33 + col + 1]
                bits.append("1" if p1 > p2 else "0")
        return "".join(bits)

    def compute_normalized_mse(self, img1: Image.Image, img2: Image.Image) -> float:
        """
        Computes normalized mean squared error (MSE) on downsampled 32x32 grayscale images.
        """
        g1 = img1.convert("L").resize((32, 32), Image.Resampling.BILINEAR)
        g2 = img2.convert("L").resize((32, 32), Image.Resampling.BILINEAR)
        
        p1 = list(g1.get_flattened_data() if hasattr(g1, "get_flattened_data") else g1.getdata())
        p2 = list(g2.get_flattened_data() if hasattr(g2, "get_flattened_data") else g2.getdata())

        total_sq_diff = sum((a - b) ** 2 for a, b in zip(p1, p2))
        mse = total_sq_diff / (32 * 32 * 255.0 * 255.0)
        return float(mse)

    def evaluate_change(self, new_data: bytes, prev_data: Optional[bytes]) -> SceneChangeResult:
        """
        Evaluates whether the frame has changed significantly enough to warrant Vision analysis.
        Execution latency: < 5ms.
        """
        if not prev_data:
            return SceneChangeResult(
                should_analyze=True,
                score=1.0,
                reason="Initial session keyframe"
            )

        t0 = time.time()
        try:
            with Image.open(io.BytesIO(new_data)) as new_img, Image.open(io.BytesIO(prev_data)) as prev_img:
                mse_score = self.compute_normalized_mse(new_img, prev_img)
                dhash1 = self.compute_dhash(new_img)
                dhash2 = self.compute_dhash(prev_img)
                
                dhash_diff = sum(b1 != b2 for b1, b2 in zip(dhash1, dhash2))
                
                # Trigger if MSE >= threshold OR dHash bit difference >= dhash_threshold
                should_analyze = (mse_score >= self.threshold) or (dhash_diff >= self.dhash_threshold)
                reason = "Significant scene change detected" if should_analyze else "Stable scene — no significant movement"
                
                return SceneChangeResult(
                    should_analyze=should_analyze,
                    score=round(mse_score, 4),
                    reason=reason
                )
        except Exception as e:
            # Fallback on error to ensure user request is not blocked
            return SceneChangeResult(
                should_analyze=True,
                score=1.0,
                reason=f"Frame comparison fallback: {str(e)}"
            )

# Singleton Instance
scene_change_detector = SceneChangeDetector()
