import sys
import os
import io
import asyncio
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.abspath("backend"))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def create_image(width=150, height=150, bg_color=(255, 255, 255), draw_fn=None):
    img = Image.new("RGB", (width, height), color=bg_color)
    if draw_fn:
        draw = ImageDraw.Draw(img)
        draw_fn(draw, width, height)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

async def run_extended_audit():
    print("\n--- WAITING 6 SECONDS FOR RATE LIMIT COOL-DOWN ---")
    await asyncio.sleep(6)

    print("\n--- TEST L: 3-Image Ordering ---")
    img1 = create_image(100, 100, (255, 0, 0), lambda d, w, h: d.text((20, 40), "ONE", fill=(255,255,255)))
    img2 = create_image(100, 100, (0, 255, 0), lambda d, w, h: d.text((20, 40), "TWO", fill=(0,0,0)))
    img3 = create_image(100, 100, (0, 0, 255), lambda d, w, h: d.text((20, 40), "THREE", fill=(255,255,255)))

    files = [
        ("images", ("one.png", img1, "image/png")),
        ("images", ("two.png", img2, "image/png")),
        ("images", ("three.png", img3, "image/png"))
    ]
    resp = client.post("/api/vision/analyze", data={"prompt": "Identify each image by number (Image 1, Image 2, Image 3)."}, files=files)
    print("3-Image Response:", resp.json().get("text", "")[:300])

    await asyncio.sleep(5)

    print("\n--- TEST M: Uncertainty / Blurry Image ---")
    blurry_img = Image.new("RGB", (50, 50), color=(100, 100, 100))
    blurry_img = blurry_img.filter(ImageFilter.GaussianBlur(10))
    buf = io.BytesIO()
    blurry_img.save(buf, format="PNG")
    blurry_bytes = buf.getvalue()

    resp_unc = client.post("/api/vision/analyze", data={"prompt": "What exact serial number or text is written in the center of this image?"}, files=[("images", ("blurry.png", blurry_bytes, "image/png"))])
    print("Uncertainty Response:", resp_unc.json().get("text", "")[:250])

    await asyncio.sleep(5)

    print("\n--- TEST I & J: Diagram / Flow ---")
    diagram_png = create_image(300, 150, (255, 255, 255), lambda d, w, h: (
        d.rectangle([10, 50, 70, 90], outline=(0,0,0)), d.text((20, 65), "USER", fill=(0,0,0)),
        d.text((80, 65), "->", fill=(0,0,0)),
        d.rectangle([100, 50, 160, 90], outline=(0,0,0)), d.text((110, 65), "AUTH", fill=(0,0,0)),
        d.text((170, 65), "->", fill=(0,0,0)),
        d.rectangle([190, 50, 270, 90], outline=(0,0,0)), d.text((200, 65), "DATABASE", fill=(0,0,0))
    ))
    resp_diag = client.post("/api/vision/analyze", data={"prompt": "Explain the flow shown in this diagram."}, files=[("images", ("diag.png", diagram_png, "image/png"))])
    print("Diagram Response:", resp_diag.json().get("text", "")[:250])

if __name__ == "__main__":
    asyncio.run(run_extended_audit())
