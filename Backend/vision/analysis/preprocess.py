from PIL import Image, ImageEnhance, ImageFilter
from tools.logger import log_structured, backend_log

class OCRPreprocessor:
    def to_grayscale(self, image: Image.Image) -> Image.Image:
        """Converts image to grayscale for enhanced OCR text recognition."""
        return image.convert("L")

    def enhance_contrast(self, image: Image.Image, factor: float = 1.5) -> Image.Image:
        """Enhances image contrast to distinguish text from backgrounds."""
        enhancer = ImageEnhance.Contrast(image)
        return enhancer.enhance(factor)

    def sharpen(self, image: Image.Image) -> Image.Image:
        """Applies a sharpening filter to clarify crisp character edges."""
        return image.filter(ImageFilter.SHARPEN)

    def scale_image(self, image: Image.Image, scale: float = 1.0) -> Image.Image:
        """Scales image dimensions if requested for small text resolution."""
        if scale == 1.0:
            return image
        new_width = int(image.width * scale)
        new_height = int(image.height * scale)
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def preprocess(self, image: Image.Image, scale: float = 1.0) -> Image.Image:
        """Applies full preprocessing pipeline for OCR optimization."""
        gray = self.to_grayscale(image)
        enhanced = self.enhance_contrast(gray, factor=1.6)
        sharp = self.sharpen(enhanced)
        scaled = self.scale_image(sharp, scale=scale)
        log_structured(backend_log, "INFO", f"[OCRPreprocessor] Image preprocessed ({image.width}x{image.height} -> {scaled.width}x{scaled.height})")
        return scaled

ocr_preprocessor = OCRPreprocessor()
