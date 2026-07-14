import uuid
import json
import time
import re
import asyncio
from collections import OrderedDict
import httpx
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import GROQ_API_KEY, TTS_ENGINE
from tts_engines import tts_manager

app = FastAPI(title="J.A.R.V.I.S. Core Backend API")

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

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    print(f"DEBUG_LOG: [Backend] Request reached chat_endpoint with message: {request.message}")
    if not GROQ_API_KEY:
        raise HTTPException(
            status_code=500, 
            detail="GROQ_API_KEY is not configured on the backend."
        )

    event_queue = asyncio.Queue()

    async def event_generator():
        # Keep yielding events until we hit the None sentinel
        while True:
            event = await event_queue.get()
            if event is None:
                break
            yield event

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

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.message}
        ],
        "temperature": 0.6,
        "max_tokens": 200,
        "stream": True
    }

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
            try:
                engine = tts_manager.get_engine(TTS_ENGINE)
                audio_data = await engine.synthesize(
                    text=text_segment,
                    voice=voice_gender,
                    language=tts_lang_key
                )
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

        async with httpx.AsyncClient() as client:
            try:
                print(f"DEBUG_LOG: [Backend] Calling Groq API...")
                async with client.stream(
                    "POST", 
                    "https://api.groq.com/openai/v1/chat/completions", 
                    headers=headers, 
                    json=payload, 
                    timeout=20.0
                ) as response:
                    print(f"DEBUG_LOG: [Backend] Groq API stream established. Status: {response.status_code}")
                    if response.status_code != 200:
                        await event_queue.put(f"data: {json.dumps({'type': 'error', 'content': f'Groq API error status {response.status_code}'})}\n\n")
                        await event_queue.put(None)
                        return

                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue
                        if line == "data: [DONE]":
                            break
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                token = data["choices"][0]["delta"].get("content", "")
                                if token:
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
                            except Exception:
                                pass
            except Exception as e:
                await event_queue.put(f"data: {json.dumps({'type': 'error', 'content': f'Connection failed: {str(e)}'})}\n\n")
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

    # Spawn the producer task to run in the background concurrently
    asyncio.create_task(producer_task())

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
