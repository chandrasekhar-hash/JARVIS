import uuid
import json
import time
import re
import asyncio
from typing import List, Optional, Dict, Any
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

from config import TTS_ENGINE, CORS_ORIGINS
from tts_engines import tts_manager
from tools.router import handle_agent_chat
from tools.startup import verify_startup
from tools.telemetry import task_watchdog, telemetry_manager, log_structured, backend_log, request_id_var
from tools.bridge import event_queue_var, bridge_manager
from api.autonomous import router as autonomous_router
from api.auth import router as auth_router
from api.health import router as health_router
from api.diagnostics import router as diagnostics_router
from api.vision import router as vision_router
from api.ocr import router as ocr_router
from api.web import router as web_router
from axl.boot_manager import system_boot_manager

app = FastAPI(title="J.A.R.V.I.S. Core Backend API")
app.include_router(autonomous_router)
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(diagnostics_router)
app.include_router(vision_router)
app.include_router(ocr_router)
app.include_router(web_router)


def shutdown_handler():
    print("DEBUG_LOG: [Shutdown] Shutdown/interruption signal received. Cleaning resources...")
    from autonomous.scheduler_engine import scheduler_engine
    scheduler_engine.stop()
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
async def startup_event():
    # Start task watchdog
    task_watchdog.start_watchdog()
    # Run startup verification (fails fast if keys or directories missing)
    verify_startup()
    # Initialize all backend services via SystemBootManager
    await system_boot_manager.initialize_all()
    
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
    allow_origins=CORS_ORIGINS,  # Configurable via config.py / CORS_ORIGINS env var
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
@app.get("/readiness")
async def ready_endpoint():

    details = {}
    is_ready = True
    
    # 1. Config Check
    from config import ACTIVE_PROVIDER, OLLAMA_BASE_URL
    if ACTIVE_PROVIDER == "ollama":
        has_key = True
        details["configuration"] = "valid"
    elif ACTIVE_PROVIDER == "gemini":
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
    if ACTIVE_PROVIDER == "ollama":
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3.0)
                details["ollama_connectivity"] = "connected" if res.status_code == 200 else "unreachable"
                if res.status_code != 200:
                    is_ready = False
        except Exception:
            details["ollama_connectivity"] = "unreachable"
            is_ready = False
    elif ACTIVE_PROVIDER == "gemini":
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

# ==================================================
# DESKTOP REST API ENDPOINTS
# ==================================================

@app.get("/api/desktop/apps")
async def get_desktop_apps():
    from tools.app_discovery import app_cache_manager
    apps = app_cache_manager.load_or_refresh()
    return {"count": len(apps), "apps": [app.to_dict() for app in apps[:50]]}


@app.get("/api/desktop/windows")
async def get_desktop_windows():
    from tools.desktop import window_list
    res = await window_list()
    return {"result": res}


# ==================================================
# SETTINGS REST API ENDPOINTS
# ==================================================

class SettingsRequest(BaseModel):
    active_provider: Optional[str] = None
    routing_mode: Optional[str] = None
    tts_engine: Optional[str] = None

@app.get("/api/settings")
def get_settings():
    import config
    from ai.providers.registry import provider_registry
    return {
        "active_provider": getattr(config, "ACTIVE_PROVIDER", "groq"),
        "routing_mode": getattr(config, "ROUTING_MODE", "manual"),
        "tts_engine": getattr(config, "TTS_ENGINE", "edge"),
        "registered_providers": list(provider_registry.get_registered_providers().keys())
    }

@app.post("/api/settings")
def update_settings(settings: SettingsRequest):
    import config
    if settings.active_provider:
        config.ACTIVE_PROVIDER = settings.active_provider.lower().strip()
        os.environ["ACTIVE_PROVIDER"] = config.ACTIVE_PROVIDER
    if settings.routing_mode:
        config.ROUTING_MODE = settings.routing_mode.lower().strip()
        os.environ["ROUTING_MODE"] = config.ROUTING_MODE
    if settings.tts_engine:
        config.TTS_ENGINE = settings.tts_engine.lower().strip()
        os.environ["TTS_ENGINE"] = config.TTS_ENGINE
    return {"status": "success", "settings": get_settings()}

class OllamaModelRequest(BaseModel):
    model: str

@app.get("/api/ollama/status")
def get_ollama_status():
    import config
    from ai.providers.registry import provider_registry
    try:
        provider = provider_registry.get_provider("ollama")
        is_online = provider.health_check()
        models = provider.get_installed_models()
        return {
            "status": "online" if is_online else "offline",
            "endpoint": getattr(config, "OLLAMA_BASE_URL", "http://localhost:11434"),
            "models": models,
            "current_model": provider.model_name
        }
    except Exception as e:
        return {
            "status": "offline",
            "endpoint": getattr(config, "OLLAMA_BASE_URL", "http://localhost:11434"),
            "models": [],
            "current_model": None,
            "error": str(e)
        }

@app.get("/api/ollama/models")
def get_ollama_models():
    from ai.providers.registry import provider_registry
    try:
        provider = provider_registry.get_provider("ollama")
        models = provider.get_installed_models()
        return {"models": models}
    except Exception as e:
        return {"models": [], "error": str(e)}

@app.post("/api/ollama/model")
def set_ollama_model(req: OllamaModelRequest):
    import config
    from ai.providers.registry import provider_registry
    selected = req.model.strip()
    config.OLLAMA_MODEL = selected
    os.environ["OLLAMA_MODEL"] = selected
    try:
        provider = provider_registry.get_provider("ollama")
        provider.model_name = selected
    except Exception:
        pass
    return {"status": "success", "selected_model": selected}

@app.get("/api/providers/status")
def get_providers_status():
    import config
    from ai.providers.registry import provider_registry
    providers = {}
    registered = provider_registry.get_registered_providers()
    
    for name in registered.keys():
        try:
            p = provider_registry.get_provider(name)
            meta = p.metadata
            is_avail = True
            if name == "ollama":
                is_avail = p.health_check()
            elif name in ["groq", "gemini", "openrouter", "cerebras"]:
                is_avail = bool(getattr(p, "api_key", None))
            
            providers[name] = {
                "name": meta.name,
                "model": meta.model_name,
                "priority": meta.priority,
                "available": is_avail,
                "supports_tools": meta.supports_tools,
                "supports_streaming": meta.supported_streaming
            }
        except Exception as e:
            providers[name] = {
                "name": name.capitalize(),
                "available": False,
                "error": str(e)
            }

    return {
        "active_provider": getattr(config, "ACTIVE_PROVIDER", "groq"),
        "routing_mode": getattr(config, "ROUTING_MODE", "manual"),
        "providers": providers
    }

# ==================================================
# VISION REST API ENDPOINTS
# ==================================================


@app.get("/api/vision/status")
def get_vision_status():
    from vision import vision_service_manager
    return vision_service_manager.get_service_status()

@app.post("/api/vision/capture")
def capture_vision_snapshot():
    from vision import vision_adapter
    return vision_adapter.get_brain_visual_context()

@app.post("/api/vision/start")
def start_vision_service(fps: float = 1.0):
    from vision import vision_service_manager
    success = vision_service_manager.start_vision(fps=fps)
    return {"status": "started" if success else "failed", "fps": fps}

@app.post("/api/vision/stop")
def stop_vision_service():
    from vision import vision_service_manager
    success = vision_service_manager.stop_vision()
    return {"status": "stopped" if success else "failed"}

@app.post("/api/vision/pause")
def pause_vision_service():
    from vision import vision_service_manager
    success = vision_service_manager.pause_vision()
    return {"status": "paused" if success else "failed"}

@app.post("/api/vision/resume")
def resume_vision_service():
    from vision import vision_service_manager
    success = vision_service_manager.resume_vision()
    return {"status": "resumed" if success else "failed"}

# ==================================================
# MEMORY REST API ENDPOINTS (PHASE 4)
# ==================================================

class MemoryQueryRequest(BaseModel):
    query_text: str
    types: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    top_k: int = 5

class MemoryStoreRequest(BaseModel):
    title: str
    content: str
    type: str = "episodic"
    tags: Optional[List[str]] = None
    importance: float = 5.0

class MemoryForgetRequest(BaseModel):
    memory_id: Optional[str] = None
    tag: Optional[str] = None
    memory_type: Optional[str] = None

@app.post("/api/memory/query")
async def query_memory_api(req: MemoryQueryRequest):
    from memory import retrieval_pipeline, MemoryQuery, MemoryType
    m_types = [MemoryType(t) for t in req.types] if req.types else None
    query = MemoryQuery(query_text=req.query_text, types=m_types, tags=req.tags, top_k=req.top_k)
    pkg = await retrieval_pipeline.execute(query)
    return {
        "status": "success",
        "has_context": pkg.has_context,
        "memory_count": pkg.memory_count,
        "formatted_context": pkg.formatted_context,
        "retrieved_memories": pkg.retrieved_memories
    }

@app.post("/api/memory/store")
async def store_memory_api(req: MemoryStoreRequest):
    from memory import ObservationCapture, ingestion_pipeline
    obs = ObservationCapture.from_conversation(req.title, req.content)
    obs.tags = req.tags or []
    mem_id = await ingestion_pipeline.process_observation(obs)
    return {"status": "success", "memory_id": mem_id}

@app.post("/api/memory/forget")
async def forget_memory_api(req: MemoryForgetRequest):
    from memory import memory_manager
    if req.memory_id:
        success = await memory_manager.delete_memory(req.memory_id)
        return {"status": "success" if success else "not_found", "memory_id": req.memory_id}
    else:
        purged = await memory_manager.forget_memory(tag=req.tag, memory_type=req.memory_type)
        return {"status": "success", "purged_count": purged}

@app.get("/api/memory/graph")
async def get_memory_graph_api():
    from memory import memory_manager
    summary = await memory_manager.get_summary()
    return {
        "status": "success",
        "total_nodes": summary.total_nodes,
        "total_edges": summary.total_edges
    }

@app.get("/api/memory/summary")
async def get_memory_summary_api():
    from memory import memory_manager
    summary = await memory_manager.get_summary()
    return {
        "status": "success",
        "total_memories": summary.total_memories,
        "count_by_type": summary.count_by_type,
        "storage_bytes": summary.storage_bytes
    }

# ==================================================
# SCHEDULER REST API ENDPOINTS (PHASE 7)
# ==================================================

class CreateJobRequest(BaseModel):
    task_name: str
    schedule_expression: str = "Every day at 08:00"
    description: Optional[str] = None
    params: Optional[Dict[str, Any]] = None

class UpdateJobRequest(BaseModel):
    schedule_expression: Optional[str] = None
    description: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None

@app.get("/api/scheduler/status")
def get_scheduler_status():
    from autonomous.scheduler_engine import scheduler_engine
    return scheduler_engine.get_status_report()

@app.get("/api/scheduler/jobs")
def get_scheduler_jobs():
    from autonomous.scheduler_storage import scheduler_storage
    jobs = scheduler_storage.get_all_jobs()
    return {"jobs": [j.model_dump() for j in jobs]}

@app.post("/api/scheduler/jobs")
def create_scheduler_job(req: CreateJobRequest):
    from autonomous.scheduler_models import ScheduledJob, JobStatus
    from autonomous.schedule_parser import parse_natural_language_schedule, compute_next_run
    from autonomous.scheduler_storage import scheduler_storage
    from autonomous.task_registry import task_registry
    
    task_def = task_registry.get_task_definition(req.task_name)
    desc = req.description or (task_def.description if task_def else f"Scheduled task {req.task_name}")
    trigger = parse_natural_language_schedule(req.schedule_expression)
    next_run = compute_next_run(trigger)
    
    job_id = f"job_{req.task_name}_{uuid.uuid4().hex[:6]}"
    job = ScheduledJob(
        job_id=job_id,
        task_name=req.task_name,
        description=desc,
        trigger=trigger,
        enabled=True,
        next_run=next_run,
        status=JobStatus.SCHEDULED,
        params=req.params or {}
    )
    scheduler_storage.save_job(job)
    return {"status": "success", "job": job.model_dump()}

@app.put("/api/scheduler/jobs/{job_id}")
def update_scheduler_job(job_id: str, req: UpdateJobRequest):
    from autonomous.scheduler_storage import scheduler_storage
    from autonomous.schedule_parser import parse_natural_language_schedule, compute_next_run
    
    job = scheduler_storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
        
    if req.schedule_expression:
        job.trigger = parse_natural_language_schedule(req.schedule_expression)
        job.next_run = compute_next_run(job.trigger)
    if req.description:
        job.description = req.description
    if req.params is not None:
        job.params = req.params
    if req.enabled is not None:
        job.enabled = req.enabled
        
    scheduler_storage.save_job(job)
    return {"status": "success", "job": job.model_dump()}

@app.delete("/api/scheduler/jobs/{job_id}")
def delete_scheduler_job(job_id: str):
    from autonomous.scheduler_storage import scheduler_storage
    success = scheduler_storage.delete_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return {"status": "success", "deleted_job_id": job_id}

@app.post("/api/scheduler/jobs/{job_id}/run")
async def run_scheduler_job_now(job_id: str):
    from autonomous.scheduler_engine import scheduler_engine
    record = await scheduler_engine.execute_job(job_id, is_manual_trigger=True)
    return {"status": "success", "execution": record.model_dump()}

@app.post("/api/scheduler/jobs/{job_id}/pause")
def pause_scheduler_job(job_id: str):
    from autonomous.scheduler_engine import scheduler_engine
    try:
        job = scheduler_engine.pause_job(job_id)
        return {"status": "success", "job": job.model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/api/scheduler/jobs/{job_id}/resume")
def resume_scheduler_job(job_id: str):
    from autonomous.scheduler_engine import scheduler_engine
    try:
        job = scheduler_engine.resume_job(job_id)
        return {"status": "success", "job": job.model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/scheduler/jobs/{job_id}/history")
def get_scheduler_job_history(job_id: str, limit: int = 50):
    from autonomous.scheduler_storage import scheduler_storage
    history = scheduler_storage.get_job_history(job_id, limit=limit)
    return {"job_id": job_id, "history": [h.model_dump() for h in history]}

@app.get("/api/scheduler/tasks")
def get_registered_tasks():
    from autonomous.task_registry import task_registry
    tasks = task_registry.get_all_tasks()
    return {"tasks": [t.model_dump() for t in tasks]}

# ==================================================
# PLUGIN REST API ENDPOINTS (PHASE 6)
# ==================================================

@app.get("/api/plugins")
def get_all_plugins():
    from plugins.plugin_manager import plugin_manager
    plugins = plugin_manager.get_all_plugins()
    return {"plugins": [p.model_dump() for p in plugins]}

@app.get("/api/plugins/{plugin_id}")
def get_plugin_details(plugin_id: str):
    from plugins.plugin_manager import plugin_manager
    state = plugin_manager.get_plugin(plugin_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found.")
    return {"plugin": state.model_dump()}

@app.post("/api/plugins/{plugin_id}/enable")
def enable_plugin_api(plugin_id: str):
    from plugins.plugin_manager import plugin_manager
    success = plugin_manager.enable_plugin(plugin_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to enable plugin '{plugin_id}'.")
    return {"status": "success", "plugin_id": plugin_id, "action": "enabled"}

@app.post("/api/plugins/{plugin_id}/disable")
def disable_plugin_api(plugin_id: str):
    from plugins.plugin_manager import plugin_manager
    success = plugin_manager.disable_plugin(plugin_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to disable plugin '{plugin_id}'.")
    return {"status": "success", "plugin_id": plugin_id, "action": "disabled"}

@app.post("/api/plugins/{plugin_id}/reload")
def reload_plugin_api(plugin_id: str):
    from plugins.plugin_manager import plugin_manager
    success = plugin_manager.reload_plugin(plugin_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to reload plugin '{plugin_id}'.")
    return {"status": "success", "plugin_id": plugin_id, "action": "reloaded"}

@app.get("/api/plugins/{plugin_id}/health")
def check_plugin_health_api(plugin_id: str):
    from plugins.plugin_manager import plugin_manager
    is_healthy = plugin_manager.health_check(plugin_id)
    state = plugin_manager.get_plugin(plugin_id)
    return {
        "plugin_id": plugin_id,
        "health_ok": is_healthy,
        "status": state.status if state else "unknown"
    }

# ==================================================
# IDENTITY & SECURITY REST API ENDPOINTS (PHASE 8.1)
# ==================================================

@app.get("/api/identity")
def get_identity():
    from identity.identity_manager import identity_manager
    user = identity_manager.get_user_profile()
    return {"user_profile": user.model_dump()}

@app.put("/api/identity")
def update_identity(body: Dict[str, Any]):
    from identity.identity_manager import identity_manager
    display_name = body.get("display_name")
    email = body.get("email")
    avatar_url = body.get("avatar_url")
    preferences = body.get("preferences")
    updated = identity_manager.update_user_profile(
        display_name=display_name,
        email=email,
        avatar_url=avatar_url,
        preferences=preferences
    )
    return {"status": "success", "user_profile": updated.model_dump()}

@app.get("/api/device")
def get_device():
    from identity.identity_manager import identity_manager
    device = identity_manager.get_device_profile()
    return {"device_profile": device.model_dump()}

@app.put("/api/device/trust")
def update_device_trust(body: Dict[str, Any]):
    from identity.identity_manager import identity_manager
    from identity.identity_models import DeviceTrustState
    trust_str = body.get("trust_state", "trusted").lower()
    try:
        trust_state = DeviceTrustState(trust_str)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid trust_state '{trust_str}'. Allowed: untrusted, provisional, trusted, revoked.")
    updated = identity_manager.update_device_trust_state(trust_state)
    return {"status": "success", "device_profile": updated.model_dump()}

@app.get("/api/security/status")
def get_security_status_api():
    from identity.identity_manager import identity_manager
    status = identity_manager.get_security_status()
    return {"security_status": status.model_dump()}

@app.post("/api/session/issue")
def issue_session_api():
    from identity.identity_manager import identity_manager
    from identity.session_manager import session_manager
    user = identity_manager.get_user_profile()
    device = identity_manager.get_device_profile()
    token_pair, session = session_manager.issue_session(user.user_id, device.device_id)
    return {
        "status": "success",
        "token_pair": token_pair.model_dump(),
        "session": session.model_dump()
    }

@app.post("/api/session/logout")
def logout_session_api(body: Dict[str, Any]):
    from identity.session_manager import session_manager
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    success = session_manager.revoke_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return {"status": "success", "session_id": session_id, "action": "revoked"}

@app.post("/api/session/refresh")
def refresh_session_api(body: Dict[str, Any]):
    from identity.session_manager import session_manager
    refresh_token = body.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="refresh_token is required")
    success, token_pair, err = session_manager.refresh_session(refresh_token)
    if not success or not token_pair:
        raise HTTPException(status_code=401, detail=err or "Token refresh failed")
    return {"status": "success", "token_pair": token_pair.model_dump()}

from api.auth import DeleteAccountRequest, delete_account

@app.post("/api/account/delete")
@app.delete("/api/account/delete")
@app.post("/api/auth/delete-account")
@app.delete("/api/auth/delete-account")
@app.post("/api/auth/account")
@app.delete("/api/auth/account")
@app.post("/api/account")
@app.delete("/api/account")
@app.post("/account/delete")
@app.delete("/account/delete")
@app.post("/auth/delete-account")
@app.delete("/auth/delete-account")
def direct_app_delete_account(body: DeleteAccountRequest, request: Request, response: Response):
    return delete_account(body, request, response)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

