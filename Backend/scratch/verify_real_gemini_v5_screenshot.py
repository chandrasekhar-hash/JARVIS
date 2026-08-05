"""
Real Gemini V5 Screenshot Intelligence Benchmark.
Tests live Gemini multimodal responses for 4 screenshot categories:
1. VS Code IDE understanding
2. Python traceback terminal
3. Chrome 404 DevTools console
4. Dashboard KPI cards

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

def make_png(text: str, width=700, height=500, bg=(25, 25, 30), fg=(210, 210, 215)) -> bytes:
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
    print("=== REAL GEMINI V5 SCREENSHOT BENCHMARK ===\n")

    # --- 1. VS CODE IDE ---
    vscode_img = make_png(
        "VS Code — main.py\n"
        "1: import fastapi\n"
        "2: from models import User  ← red underline\n"
        "3:\n"
        "4: app = FastAPI()\n"
        "\n"
        "PROBLEMS:\n"
        "models.py:2 — ModuleNotFoundError: No module named 'models'"
    )
    t0 = time.time()
    r = client.post("/api/vision/analyze",
        data={"prompt": "What error is shown in VS Code and why?"},
        files=[("images", ("vscode.png", vscode_img, "image/png"))]
    )
    res = r.json()
    print("--- 1. VS CODE IDE ---")
    print(f"Task Type: {res.get('task_type')}  |  Latency: {time.time()-t0:.2f}s")
    print(f"Response:\n{res.get('text','')[:400]}\n")

    await asyncio.sleep(5)

    # --- 2. PYTHON TRACEBACK TERMINAL ---
    term_img = make_png(
        "$ python app.py\n"
        "Traceback (most recent call last):\n"
        "  File 'app.py', line 7, in <module>\n"
        "    from database import db_connect\n"
        "  File 'database.py', line 3, in <module>\n"
        "    import psycopg2\n"
        "ModuleNotFoundError: No module named 'psycopg2'\n"
        "\n"
        "Process finished with exit code 1"
    )
    t0 = time.time()
    r = client.post("/api/vision/analyze",
        data={"prompt": "What is happening in this terminal output and how do I fix it?"},
        files=[("images", ("terminal.png", term_img, "image/png"))]
    )
    res = r.json()
    print("--- 2. PYTHON TRACEBACK TERMINAL ---")
    print(f"Task Type: {res.get('task_type')}  |  Latency: {time.time()-t0:.2f}s")
    print(f"Response:\n{res.get('text','')[:400]}\n")

    await asyncio.sleep(5)

    # --- 3. CHROME DEVTOOLS NETWORK TAB ---
    devtools_img = make_png(
        "Chrome DevTools > Console\n"
        "✖ Access to fetch at 'http://api.example.com/user' from origin\n"
        "  'http://localhost:3000' has been blocked by CORS policy:\n"
        "  No 'Access-Control-Allow-Origin' header is present\n"
        "\n"
        "✖ Uncaught TypeError: Cannot read properties of undefined\n"
        "  at UserComponent (App.js:42)\n"
        "\n"
        "Network > POST /api/login  401 Unauthorized  240ms"
    )
    t0 = time.time()
    r = client.post("/api/vision/analyze",
        data={"prompt": "What errors are in this Chrome DevTools console and what do they mean?"},
        files=[("images", ("devtools.png", devtools_img, "image/png"))]
    )
    res = r.json()
    print("--- 3. CHROME DEVTOOLS CONSOLE ---")
    print(f"Task Type: {res.get('task_type')}  |  Latency: {time.time()-t0:.2f}s")
    print(f"Response:\n{res.get('text','')[:400]}\n")

    await asyncio.sleep(5)

    # --- 4. DASHBOARD KPIs ---
    dash_img = make_png(
        "Analytics Dashboard — Aug 2026\n"
        "\n"
        "┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐\n"
        "│  DAU: 12,450    │  │ Revenue: $45,200 │  │ Error Rate: 0.2%│\n"
        "│  (+8% vs last)  │  │  (+12% vs last)  │  │  (▼ 0.1%)       │\n"
        "└─────────────────┘  └─────────────────┘  └─────────────────┘\n"
        "\n"
        "Sessions by Platform: Mobile 68% | Desktop 32%\n"
        "⚠ Warning: API latency spike at 14:30 UTC"
    , fg=(220, 220, 230))
    t0 = time.time()
    r = client.post("/api/vision/analyze",
        data={"prompt": "Explain this analytics dashboard and highlight anything important"},
        files=[("images", ("dashboard.png", dash_img, "image/png"))]
    )
    res = r.json()
    print("--- 4. ANALYTICS DASHBOARD ---")
    print(f"Task Type: {res.get('task_type')}  |  Latency: {time.time()-t0:.2f}s")
    print(f"Response:\n{res.get('text','')[:400]}\n")

    print("=== BENCHMARK COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(benchmark())
