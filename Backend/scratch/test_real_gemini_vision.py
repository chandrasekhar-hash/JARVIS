import os
import io
import asyncio
from PIL import Image, ImageDraw

from intelligence.vision.models import VisionRequest, VisionImageItem
from intelligence.vision.providers.gemini_vision import GeminiVisionProvider

async def main():
    print("--- REAL MANUALLY EXECUTED GEMINI VISION TEST ---")
    
    # Create a real test image with explicit visual content (a bright red square on yellow background with text "JARVIS VISION TEST")
    img = Image.new("RGB", (300, 300), color=(255, 255, 0)) # Yellow background
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 250, 250], fill=(255, 0, 0)) # Red box in center
    draw.text((60, 60), "JARVIS VISION", fill=(255, 255, 255))
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()

    image_item = VisionImageItem(
        filename="test_real_visual.png",
        content_type="image/png",
        data=img_bytes,
        size=len(img_bytes)
    )

    req = VisionRequest(
        prompt="Describe this image in detail. What shapes, colors, and text are visible?",
        images=[image_item]
    )

    provider = GeminiVisionProvider()
    print("Sending real image payload to Gemini Vision API...")
    result = await provider.analyze(req)
    
    print("\n--- GEMINI VISION API RESPONSE ---")
    print(f"Provider: {result.provider}")
    print(f"Model: {result.model}")
    print(f"Image Count: {result.image_count}")
    print(f"Text output:\n{result.text}\n")

if __name__ == "__main__":
    asyncio.run(main())
