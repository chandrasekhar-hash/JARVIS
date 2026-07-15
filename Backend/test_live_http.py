"""
Live HTTP test against the running FastAPI server.
Sends real /api/chat POST requests and streams the response.
"""
import httpx
import json

BASE = "http://localhost:8000"

# Health check first
r = httpx.get(f"{BASE}/health", timeout=5)
print("Health:", r.json())
print()

commands = ["Open YouTube", "Open Chrome", "Open VS Code", "Close Chrome"]

for cmd in commands:
    print(f"--- Sending: {cmd!r} ---")
    try:
        with httpx.stream(
            "POST", f"{BASE}/api/chat",
            json={"message": cmd, "voice": "female", "language": "english"},
            timeout=30.0
        ) as resp:
            full_text = ""
            error_seen = None
            for line in resp.iter_lines():
                if line.startswith("data:"):
                    try:
                        payload = json.loads(line[5:].strip())
                        ptype = payload.get("type")
                        if ptype == "text":
                            full_text += payload.get("content", "")
                        elif ptype == "error":
                            error_seen = payload.get("content", "")
                    except Exception:
                        pass
            if error_seen:
                print(f"  RESULT (ERROR): {error_seen}")
            else:
                print(f"  RESULT: {full_text}")
    except Exception as e:
        print(f"  HTTP Error: {e}")
    print()

print("=== Live test complete ===")
