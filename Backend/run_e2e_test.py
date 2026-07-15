"""
End-to-end test: sends 'Open YouTube' to the backend and verifies every stage.
"""
import httpx
import json

BASE = "http://localhost:8000"

print("=== Stage 1: Health Check ===")
r = httpx.get(f"{BASE}/health", timeout=5)
print(f"GET /health => {r.status_code} | {r.json()}")

print()
print("=== Stage 2: POST /api/chat  message='Open YouTube' ===")
payload_sent = {"message": "Open YouTube", "voice": "female", "language": "english"}
print(f"Request payload: {json.dumps(payload_sent)}")
print()

full_text = ""
audio_urls = []
errors = []

with httpx.stream(
    "POST", f"{BASE}/api/chat",
    json=payload_sent,
    timeout=30.0
) as resp:
    print(f"Response status:   {resp.status_code}")
    print(f"Content-Type:      {resp.headers.get('content-type', '')}")
    print()
    for line in resp.iter_lines():
        if line.startswith("data:"):
            try:
                event = json.loads(line[5:].strip())
                ptype = event.get("type")
                if ptype == "text":
                    full_text += event.get("content", "")
                elif ptype == "audio_url":
                    audio_urls.append(event.get("url", ""))
                elif ptype == "error":
                    errors.append(event.get("content", ""))
            except Exception as ex:
                print(f"  Parse error: {ex}")

print("=== Stage 3: Results ===")
print(f"JARVIS response text : {repr(full_text)}")
print(f"Audio URL segments   : {len(audio_urls)}")
for u in audio_urls:
    print(f"  -> {u}")
if errors:
    print("ERRORS RETURNED:")
    for e in errors:
        print(f"  ERROR: {e}")
else:
    print("No errors in stream.")

print()
print("=== Stage 4: Metrics after request ===")
r2 = httpx.get(f"{BASE}/metrics", timeout=5)
m = r2.json()
llm = m.get("llm_requests", "N/A")
tts = m.get("tts_requests", "N/A")
print(f"LLM requests : {llm}")
print(f"TTS requests : {tts}")

print()
print("=== DONE ===")
