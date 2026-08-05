"""
Real Gemini V6 Multi-Image Intelligence Benchmark.
Tests live Gemini multimodal cross-image responses for 5 multi-image scenarios:
1. Before/after website redesign
2. Two code screenshots (OCR + Vision comparison)
3. Three construction progress images (Timeline & Progress tracking)
4. Dashboard revisions (KPI metrics & Chart changes)
5. Document comparison (Inconsistencies & OCR text diffing)

Rate-limited at 5 RPM with 5s pauses.
"""
import sys
import os
import io
import time
import asyncio
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.abspath("backend"))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def make_png(text: str, width=650, height=450, bg=(25, 25, 30), fg=(210, 210, 215)) -> bytes:
    img = Image.new("RGB", (width, height), color=bg)
    draw = ImageDraw.Draw(img)
    lines = text.split("\n")
    y = 15
    for line in lines:
        draw.text((15, y), line, fill=fg)
        y += 20
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

async def benchmark():
    print("=== REAL GEMINI V6 MULTI-IMAGE BENCHMARK ===\n")

    # --- 1. BEFORE / AFTER WEBSITE REDESIGN ---
    web_v1 = make_png(
        "Website v1.0 — Old Design\n"
        "Header: ACME Corp\n"
        "Hero: Basic Cloud Solutions\n"
        "Button: Click Here [Gray]\n"
        "Footer: Copyright 2024"
    )
    web_v2 = make_png(
        "Website v2.0 — Redesign 2026\n"
        "Header: ACME Corp + Dark Mode Toggle\n"
        "Hero: Enterprise AI Cloud Infrastructure\n"
        "Button: Start Free Trial [Bright Green]\n"
        "Badge: SOC2 Certified | 99.99% Uptime\n"
        "Footer: Copyright 2026"
    )

    t0 = time.time()
    r = client.post("/api/vision/multi-image",
        data={"prompt": "Compare this website before and after redesign. What changed?"},
        files=[
            ("images", ("v1.png", web_v1, "image/png")),
            ("images", ("v2.png", web_v2, "image/png"))
        ]
    )
    res = r.json()
    print("--- 1. BEFORE/AFTER WEBSITE REDESIGN ---")
    print(f"Task Type: {res.get('task_type')}  |  Latency: {time.time()-t0:.2f}s")
    print(f"Summary: {res.get('visual_summary')}")
    print(f"Relationships: {res.get('relationships')}")
    print(f"Response:\n{res.get('text','')[:400]}\n")

    await asyncio.sleep(5)

    # --- 2. TWO CODE SCREENSHOTS ---
    code_1 = make_png(
        "main.py (Original)\n"
        "1: def calculate_total(prices):\n"
        "2:     total = 0\n"
        "3:     for p in prices:\n"
        "4:         total += p\n"
        "5:     return total"
    )
    code_2 = make_png(
        "main.py (Refactored)\n"
        "1: from typing import List\n"
        "2: import logging\n"
        "3:\n"
        "4: def calculate_total(prices: List[float], tax_rate: float = 0.05) -> float:\n"
        "5:     \"\"\"Calculates total price including default 5% tax.\"\"\"\n"
        "6:     subtotal = sum(prices)\n"
        "7:     return round(subtotal * (1 + tax_rate), 2)"
    )

    t0 = time.time()
    r = client.post("/api/vision/multi-image",
        data={"prompt": "Compare these two code screenshots. What imports, functions, and tax logic were added?"},
        files=[
            ("images", ("code1.png", code_1, "image/png")),
            ("images", ("code2.png", code_2, "image/png"))
        ]
    )
    res = r.json()
    print("--- 2. TWO CODE SCREENSHOTS ---")
    print(f"Task Type: {res.get('task_type')}  |  Latency: {time.time()-t0:.2f}s")
    print(f"OCR Used: {res.get('metadata', {}).get('ocr_used')}")
    print(f"Summary: {res.get('visual_summary')}")
    print(f"Response:\n{res.get('text','')[:400]}\n")

    await asyncio.sleep(5)

    # --- 3. THREE CONSTRUCTION PROGRESS IMAGES ---
    stage_1 = make_png("Construction Site — Month 1\nStatus: Ground excavation and clearing\nCompletion: 15%")
    stage_2 = make_png("Construction Site — Month 3\nStatus: Concrete foundation poured & steel columns erected\nCompletion: 45%")
    stage_3 = make_png("Construction Site — Month 6\nStatus: Full structure framed, exterior glass panels installed\nCompletion: 85%")

    t0 = time.time()
    r = client.post("/api/vision/multi-image",
        data={"prompt": "Track the construction progress across these three stage images over time."},
        files=[
            ("images", ("month1.png", stage_1, "image/png")),
            ("images", ("month3.png", stage_2, "image/png")),
            ("images", ("month6.png", stage_3, "image/png"))
        ]
    )
    res = r.json()
    print("--- 3. THREE CONSTRUCTION PROGRESS IMAGES ---")
    print(f"Task Type: {res.get('task_type')}  |  Latency: {time.time()-t0:.2f}s")
    print(f"Summary: {res.get('visual_summary')}")
    print(f"Response:\n{res.get('text','')[:400]}\n")

    await asyncio.sleep(5)

    # --- 4. DASHBOARD REVISIONS ---
    dash_orig = make_png(
        "Analytics Dashboard — Q1\n"
        "DAU: 10,000 | MRR: $50,000 | Churn: 2.1%\n"
        "Chart: Flat trend"
    )
    dash_revised = make_png(
        "Analytics Dashboard — Q2\n"
        "DAU: 18,500 (+85%) | MRR: $92,000 (+84%) | Churn: 1.2% (▼ 0.9%)\n"
        "Chart: Steep upward growth slope"
    )

    t0 = time.time()
    r = client.post("/api/vision/multi-image",
        data={"prompt": "Compare these two dashboard revisions. What metrics improved?"},
        files=[
            ("images", ("dash1.png", dash_orig, "image/png")),
            ("images", ("dash2.png", dash_revised, "image/png"))
        ]
    )
    res = r.json()
    print("--- 4. DASHBOARD REVISIONS ---")
    print(f"Task Type: {res.get('task_type')}  |  Latency: {time.time()-t0:.2f}s")
    print(f"Summary: {res.get('visual_summary')}")
    print(f"Response:\n{res.get('text','')[:400]}\n")

    await asyncio.sleep(5)

    # --- 5. DOCUMENT COMPARISON ---
    doc_1 = make_png(
        "Service Agreement (Page 1)\n"
        "Client: Acme Corp\n"
        "Payment Terms: Net 30\n"
        "Monthly Retainer: $5,000\n"
        "Termination Notice: 30 days"
    )
    doc_2 = make_png(
        "Service Agreement (Page 2 / Addendum)\n"
        "Client: Acme Corp\n"
        "Payment Terms: Net 60  ← (Mismatch!)\n"
        "Monthly Retainer: $6,500 ← (Increased!)\n"
        "Termination Notice: 30 days"
    )

    t0 = time.time()
    r = client.post("/api/vision/multi-image",
        data={"prompt": "Check for inconsistencies and changes between these two service agreement pages."},
        files=[
            ("images", ("doc1.png", doc_1, "image/png")),
            ("images", ("doc2.png", doc_2, "image/png"))
        ]
    )
    res = r.json()
    print("--- 5. DOCUMENT COMPARISON ---")
    print(f"Task Type: {res.get('task_type')}  |  Latency: {time.time()-t0:.2f}s")
    print(f"Summary: {res.get('visual_summary')}")
    print(f"Inconsistencies: {res.get('structured_comparison', {}).get('inconsistencies')}")
    print(f"Response:\n{res.get('text','')[:400]}\n")

    print("=== BENCHMARK COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(benchmark())
