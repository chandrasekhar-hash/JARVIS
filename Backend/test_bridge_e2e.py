import sys
import os
import asyncio
import httpx
import uvicorn
import threading
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from pydantic import BaseModel
from tools.registry import registry
from tools.bridge import bridge_manager, event_queue_var
from main import app  # import the main app

# 1. Register our mock testing tool
@registry.register(
    name="test_bridge_op",
    description="A test tool that requests a window list via the bridge.",
    parameters={"type": "object", "properties": {}}
)
async def test_bridge_op():
    print("DEBUG_LOG: [TestTool] test_bridge_op invoked, calling bridge_manager...")
    res = await bridge_manager.run_desktop_op("window:list", {"test": "args"}, timeout=5.0)
    print(f"DEBUG_LOG: [TestTool] bridge_manager returned: {res}")
    return f"Bridge successful: {res}"

# Override router logic or trigger it via custom test request
@app.get("/test-run-bridge")
async def test_run_bridge():
    # Setup mock event queue
    queue = asyncio.Queue()
    event_queue_var.set(queue)

    # Spawn the tool execution task
    tool_task = asyncio.create_task(registry.execute("test_bridge_op"))

    # Get the request packet from the queue
    try:
        request_packet = await asyncio.wait_for(queue.get(), timeout=2.0)
        print(f"DEBUG_LOG: [TestServer] Got bridge request packet: {request_packet}")
        
        # Extract request ID
        import json
        clean_data = request_packet.strip().replace("data:", "").strip()
        payload = json.loads(clean_data)
        req_id = payload["id"]
        
        # Simulate callback from React/Tauri
        async with httpx.AsyncClient() as client:
            res = await client.post("http://127.0.0.1:8081/api/bridge/callback", json={
                "id": req_id,
                "data": [{"handle": 1234, "title": "Test Window"}]
            })
            print(f"DEBUG_LOG: [TestServer] Callback response status: {res.status_code}")

        # Wait for tool to complete
        result = await asyncio.wait_for(tool_task, timeout=2.0)
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "failed", "error": str(e)}

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8081, log_level="error")

async def test_flow():
    # Start server in thread
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(1.5)  # Wait for uvicorn to boot

    print("=== [TEST] Starting Bridge E2E Test Flow ===")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get("http://127.0.0.1:8081/test-run-bridge", timeout=10.0)
            print(f"Response Status: {resp.status_code}")
            print(f"Response Body: {resp.json()}")
            
            data = resp.json()
            if data.get("status") == "success" and "Bridge successful" in data.get("result"):
                print("PASS: Bridge end-to-end communication resolved successfully!")
                sys.exit(0)
            else:
                print("FAIL: Bridge failed to resolve or returned wrong result.")
                sys.exit(1)
        except Exception as e:
            print(f"FAIL: Exception in E2E test: {e}")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_flow())
