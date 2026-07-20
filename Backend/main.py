import uuid
import json
import time
import re
import asyncio
from collections import OrderedDict
import httpx
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import psutil
import signal
import atexit
import os

from config import TTS_ENGINE
from tts_engines import tts_manager
from tools.router import handle_agent_chat
from tools.startup import verify_startup
from tools.telemetry import task_watchdog, telemetry_manager, log_structured, backend_log, request_id_var
from tools.bridge import event_queue_var, bridge_manager

app = FastAPI(title="J.A.R.V.I.S. Core Backend API")

def shutdown_handler():
    print("DEBUG_LOG: [Shutdown] Shutdown/interruption signal received. Cleaning resources...")
    task_watchdog.cancel_all_tasks()
    from tools.locks import destructive_lock, _tool_locks
    try:
        if destructive_lock.locked():
            destructive_lock.release()
        for lock in _tool_locks.values():
            if lock.locked():
                lock.release()
    except Exception:
        pass
    print("DEBUG_LOG: [Shutdown] Clean recovery completed.")

@app.on_event("startup")
def startup_event():
    # Start task watchdog
    task_watchdog.start_watchdog()
    # Run startup verification (fails fast if keys or directories missing)
    verify_startup()
    
    # Register shutdown signals / exit handlers for recovery
    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, shutdown_handler)
    except (NotImplementedError, ValueError):
        atexit.register(shutdown_handler)

# Enable CORS for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-Memory Cache for temporary audio files to avoid base64 transport overhead
class AudioCache:
    def __init__(self, max_size=100):
        self.cache = OrderedDict()
        self.max_size = max_size

    def set(self, key: str, value: bytes):
        if len(self.cache) >= self.max_size:
            # Remove oldest item
            self.cache.popitem(last=False)
        self.cache[key] = (value, time.time())

    def get(self, key: str) -> bytes:
        if key in self.cache:
            value, _ = self.cache[key]
            # Refresh LRU ordering
            self.cache.move_to_end(key)
            return value
        return None

audio_cache = AudioCache()

class ChatRequest(BaseModel):
    message: str
    voice: str = "female"
    language: str = "english"
    tts_language: str = ""  # Optional: explicit TTS voice language; falls back to `language` when empty
    assistant_name: str = "J.A.R.V.I.S"
    creator: str = "Chandrasekhar"

@app.get("/api/voices")
async def get_voices():
    # Return available configurations to populate voice selectors dynamically
    return {
        "engines": ["edge"],
        "languages": [
            "English", "Hindi", "Hinglish", "Telugu", "Tamil", "Odia", 
            "Kannada", "Malayalam", "Bengali", "Gujarati", "Punjabi", "Marathi"
        ],
        "genders": ["Female", "Male"]
    }

@app.get("/api/audio/{audio_id}")
async def get_audio(audio_id: str):
    audio_bytes = audio_cache.get(audio_id)
    if not audio_bytes:
        raise HTTPException(status_code=404, detail="Audio file not found or expired")
    
    return Response(content=audio_bytes, media_type="audio/mpeg")

class TTSRequest(BaseModel):
    text: str
    voice: str = "female"
    language: str = "english"

@app.post("/api/tts")
async def tts_endpoint(request: TTSRequest):
    lang_key = request.language.lower().strip()
    voice_gender = request.voice.lower().strip()
    try:
        engine = tts_manager.get_engine(TTS_ENGINE)
        audio_data = await engine.synthesize(
            text=request.text,
            voice=voice_gender,
            language=lang_key
        )
        audio_id = str(uuid.uuid4())
        audio_cache.set(audio_id, audio_data)
        return {"url": f"/api/audio/{audio_id}"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"TTS synthesis failed: {str(e)}"
        )

@app.get("/api/system_info")
async def system_info_endpoint():
    import platform
    import subprocess
    
    # 1. Location lookup via IP
    location_data = {
        "city": "Bengaluru",
        "country": "India",
        "countryCode": "IN",
        "lat": 12.9716,
        "lon": 77.5946
    }
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get("http://ip-api.com/json/", timeout=1.5)
            if res.status_code == 200:
                data = res.json()
                if data.get("status") == "success":
                    location_data = {
                        "city": data.get("city", "Delhi"),
                        "country": data.get("country", "India"),
                        "countryCode": data.get("countryCode", "IN"),
                        "lat": data.get("lat", 28.6139),
                        "lon": data.get("lon", 77.2090)
                    }
    except Exception:
        pass

    # 2. Battery status
    battery = psutil.sensors_battery()
    battery_data = {
        "percent": battery.percent if battery else 100,
        "power_plugged": battery.power_plugged if battery else True,
        "secsleft": battery.secsleft if battery else -1
    }

    # 3. WiFi Status
    wifi_connected = False
    wifi_ssid = "Not Connected"
    current_os = platform.system().lower()
    
    if "windows" in current_os:
        try:
            out = subprocess.check_output("netsh wlan show interfaces", shell=True, text=True, errors="ignore")
            ssid_match = re.search(r"^\s+SSID\s+:\s+(.+)$", out, re.MULTILINE)
            state_match = re.search(r"^\s+State\s+:\s+(connected|connected\s.*)$", out, re.MULTILINE)
            if state_match:
                wifi_connected = True
                wifi_ssid = ssid_match.group(1).strip() if ssid_match else "Local WiFi Connection"
        except Exception:
            pass
    elif "darwin" in current_os:
        try:
            out = subprocess.check_output(["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-I"], text=True, errors="ignore")
            ssid_match = re.search(r" SSID: (.+)", out)
            if ssid_match:
                wifi_connected = True
                wifi_ssid = ssid_match.group(1).strip()
        except Exception:
            pass
    else: # Linux
        try:
            out = subprocess.check_output("iwgetid -r", shell=True, text=True, errors="ignore").strip()
            if out:
                wifi_connected = True
                wifi_ssid = out
        except Exception:
            pass

    # 4. Bluetooth status
    bluetooth_on = False
    if "windows" in current_os:
        try:
            for service in psutil.win_service_iter():
                if service.name().lower() == "bthserv":
                    if service.status() == "running":
                        bluetooth_on = True
                    break
        except Exception:
            pass
    elif "darwin" in current_os:
        try:
            out = subprocess.check_output(["defaults", "read", "/Library/Preferences/com.apple.Bluetooth", "ControllerPowerState"], text=True, errors="ignore").strip()
            if out == "1":
                bluetooth_on = True
        except Exception:
            pass
    else:
        try:
            out = subprocess.check_output("systemctl is-active bluetooth", shell=True, text=True, errors="ignore").strip()
            if out == "active":
                bluetooth_on = True
        except Exception:
            pass

    return {
        "location": location_data,
        "battery": battery_data,
        "network": {
            "wifi": {
                "connected": wifi_connected,
                "ssid": wifi_ssid
            },
            "bluetooth": {
                "enabled": bluetooth_on
            }
        },
        "time": {
            "timestamp": time.time(),
            "formatted": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    }

@app.get("/health")
def health_endpoint():
    return {"status": "healthy"}


@app.get("/ready")
async def ready_endpoint():
    details = {}
    is_ready = True
    
    # 1. Config Check
    from config import ACTIVE_PROVIDER
    if ACTIVE_PROVIDER == "gemini":
        has_key = bool(os.getenv("GEMINI_API_KEY") or os.getenv("VITE_GEMINI_API_KEY"))
        details["configuration"] = "valid" if has_key else "missing_gemini_key"
    elif ACTIVE_PROVIDER == "openrouter":
        has_key = bool(os.getenv("OPENROUTER_API_KEY") or os.getenv("VITE_OPENROUTER_API_KEY"))
        details["configuration"] = "valid" if has_key else "missing_openrouter_key"
    elif ACTIVE_PROVIDER == "cerebras":
        has_key = bool(os.getenv("CEREBRAS_API_KEY") or os.getenv("VITE_CEREBRAS_API_KEY"))
        details["configuration"] = "valid" if has_key else "missing_cerebras_key"
    else:
        has_key = bool(os.getenv("GROQ_API_KEY") or os.getenv("VITE_GROQ_API_KEY"))
        details["configuration"] = "valid" if has_key else "missing_groq_key"
    if not has_key:
        is_ready = False
        
    # 2. Tool Registry Check
    from tools.registry import registry
    num_tools = len(registry.get_tool_schemas())
    details["tool_registry"] = f"active ({num_tools} tools)" if num_tools > 0 else "empty"
    if num_tools == 0:
        is_ready = False
        
    # 3. Filesystem Check
    desktop_exists = os.path.exists(os.path.join(os.path.expanduser("~"), "Desktop"))
    details["filesystem"] = "accessible" if desktop_exists else "restricted"
    
    # 4. Connection Check
    if ACTIVE_PROVIDER == "gemini":
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get("https://generativelanguage.googleapis.com", timeout=3.0)
                details["gemini_connectivity"] = "connected"
        except Exception:
            details["gemini_connectivity"] = "unreachable"
            is_ready = False
    elif ACTIVE_PROVIDER == "openrouter":
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get("https://openrouter.ai/api/v1/models", timeout=3.0)
                details["openrouter_connectivity"] = "connected"
        except Exception:
            details["openrouter_connectivity"] = "unreachable"
            is_ready = False
    elif ACTIVE_PROVIDER == "cerebras":
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get("https://api.cerebras.ai/v1/models", timeout=3.0, headers={"Authorization": f"Bearer {os.getenv('CEREBRAS_API_KEY')}"})
                details["cerebras_connectivity"] = "connected"
        except Exception:
            details["cerebras_connectivity"] = "unreachable"
            is_ready = False
    else:
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get("https://api.groq.com", timeout=3.0)
                details["groq_connectivity"] = "connected"
        except Exception:
            details["groq_connectivity"] = "unreachable"
            is_ready = False
        
    # 5. TTS Check
    try:
        from tts_engines import tts_manager
        details["edge_tts"] = "available"
    except Exception:
        details["edge_tts"] = "failed"
        is_ready = False
        
    status_code = 200 if is_ready else 503
    return JSONResponse(status_code=status_code, content={"ready": is_ready, "details": details})

@app.get("/metrics")
def metrics_endpoint():
    summary = telemetry_manager.get_summary()
    active_list = []
    for tid, info in task_watchdog.tasks.items():
        active_list.append({
            "task_id": tid,
            "description": info["description"],
            "elapsed": round(time.time() - info["start_time"], 2)
        })
    summary["active_tasks"] = active_list
    return summary

from typing import Any, Optional

class CallbackRequest(BaseModel):
    id: str
    data: Any = None
    error: Optional[str] = None

@app.post("/api/bridge/callback")
async def bridge_callback_endpoint(req: CallbackRequest):
    resolved = await bridge_manager.resolve_request(req.id, {"data": req.data, "error": req.error})
    if resolved:
        return {"status": "success"}
    else:
        raise HTTPException(status_code=404, detail="Bridge request expired or not found")

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    req_id = str(uuid.uuid4())
    request_id_var.set(req_id)
    log_structured(backend_log, "INFO", f"Request reached chat_endpoint with message: {request.message}")
    telemetry_manager.increment_counter("active_conversations")

    event_queue = asyncio.Queue()
    event_queue_var.set(event_queue)
    prod_task = None

    async def event_generator():
        try:
            while True:
                event = await event_queue.get()
                if event is None:
                    break
                yield event
        except asyncio.CancelledError:
            print("DEBUG_LOG: [Backend] Client connection cancelled. Cleaning up tasks...")
            if prod_task and not prod_task.done():
                prod_task.cancel()
            from tools.logger import log_backend_cancellation
            log_backend_cancellation("producer_task")
            raise
        finally:
            telemetry_manager.decrement_counter("active_conversations")
            if prod_task and not prod_task.done():
                prod_task.cancel()

    # Clean inputs
    lang_key = request.language.lower().strip()
    voice_gender = request.voice.lower().strip()
    # tts_language overrides lang_key for voice synthesis when explicitly set
    tts_lang_key = request.tts_language.lower().strip() if request.tts_language.strip() else lang_key
    
    # System prompt ensuring short, calm, and confident professional assistant replies in natural Indian English.
    # No Marvel or Iron Man reference allowed. Identity strictly built from configured values.
    system_prompt = (
        f"You are {request.assistant_name}, a professional, calm, and confident AI assistant created by {request.creator}. "
        f"Provide extremely short, direct, and useful answers in natural Indian English. "
        f"Avoid any preamble, greetings, or repeating the user's question. Answer in 1-2 sentences at most, "
        f"unless the user explicitly asks for detailed explanations. "
        f"Identity boundaries:\n"
        f"- Your name is strictly: {request.assistant_name}.\n"
        f"- Your creator is strictly: {request.creator}.\n"
        f"- You have absolutely no connection to Tony Stark, Marvel, Iron Man, Stark Industries, or any other fictional universe or character. "
        f"If asked about your origin, state clearly and calmly that you were created by {request.creator}."
    )


    async def producer_task():
        sentence_buffer = ""
        tts_tasks = []
        
        # Delivery tracking to ensure TTS segments are sent in the correct order
        completed_audios = {}
        next_yield_index = 0
        audio_delivery_lock = asyncio.Lock()

        async def synthesize_task(text_segment: str, index: int):
            nonlocal next_yield_index
            text_segment = text_segment.strip()
            
            # Check if segment contains any alphanumeric character
            clean_segment = re.sub(r'[^\w\s]', '', text_segment).strip()
            if not clean_segment:
                print(f"DEBUG_LOG: [Backend] Background TTS skipped empty/punctuation-only segment [{index}]: '{text_segment}'")
                async with audio_delivery_lock:
                    completed_audios[index] = ""  # empty placeholder
                    while next_yield_index in completed_audios:
                        payload = completed_audios[next_yield_index]
                        if payload:
                            await event_queue.put(payload)
                        del completed_audios[next_yield_index]
                        next_yield_index += 1
                return

            print(f"DEBUG_LOG: [Backend] Background TTS started for sentence [{index}]: '{text_segment}'")
            t_start = time.time()
            try:
                engine = tts_manager.get_engine(TTS_ENGINE)
                audio_data = await engine.synthesize(
                    text=text_segment,
                    voice=voice_gender,
                    language=tts_lang_key
                )
                elapsed = time.time() - t_start
                telemetry_manager.record_latency("tts_latency", elapsed)
                telemetry_manager.increment_counter("tts_requests")
                audio_id = str(uuid.uuid4())
                audio_cache.set(audio_id, audio_data)
                
                event_data = f"data: {json.dumps({'type': 'audio_url', 'url': f'/api/audio/{audio_id}', 'text': text_segment})}\n\n"
                
                async with audio_delivery_lock:
                    completed_audios[index] = event_data
                    while next_yield_index in completed_audios:
                        payload = completed_audios[next_yield_index]
                        if payload:
                            await event_queue.put(payload)
                        del completed_audios[next_yield_index]
                        next_yield_index += 1
                print(f"DEBUG_LOG: [Backend] Background TTS completed for sentence [{index}]")
            except Exception as e:
                err_event = f"data: {json.dumps({'type': 'error', 'content': f'TTS synthesis failed: {str(e)}'})}\n\n"
                async with audio_delivery_lock:
                    completed_audios[index] = err_event
                    while next_yield_index in completed_audios:
                        payload = completed_audios[next_yield_index]
                        if payload:
                            await event_queue.put(payload)
                        del completed_audios[next_yield_index]
                        next_yield_index += 1

        sentence_index = 0

        try:
            print(f"DEBUG_LOG: [Backend] Routing query to Agent Router...")
            async for token in handle_agent_chat(
                message=request.message,
                assistant_name=request.assistant_name,
                creator=request.creator
            ):
                sentence_buffer += token
                # Forward text tokens instantly to the client
                await event_queue.put(f"data: {json.dumps({'type': 'text', 'content': token})}\n\n")
                
                # Extract sentences for parallel synthesis
                while True:
                    match = re.search(r'(.*?[.!?]+)\s+', sentence_buffer)
                    if match:
                        sentence = match.group(1).strip()
                        if len(sentence) >= 3:
                            # Spawn parallel background task for synthesis
                            task = asyncio.create_task(synthesize_task(sentence, sentence_index))
                            tts_tasks.append(task)
                            sentence_index += 1
                        sentence_buffer = sentence_buffer[match.end():]
                    else:
                        break
        except Exception as e:
            await event_queue.put(f"data: {json.dumps({'type': 'error', 'content': f'Agent processing failed: {str(e)}'})}\n\n")
            await event_queue.put(None)
            return
        finally:
            # Process remainder text left in buffer
            final_sentence = sentence_buffer.strip()
            if len(final_sentence) >= 2:
                task = asyncio.create_task(synthesize_task(final_sentence, sentence_index))
                tts_tasks.append(task)
                sentence_index += 1

            # Wait for all background synthesis tasks to complete
            if tts_tasks:
                await asyncio.gather(*tts_tasks, return_exceptions=True)
            
            # Signal event_generator to exit
            await event_queue.put(None)

    # Spawn the producer task and save reference for cancellation tracking
    prod_task = asyncio.create_task(producer_task())
    task_watchdog.register_task(prod_task, f"chat_producer::{req_id}", timeout=60.0)
    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
