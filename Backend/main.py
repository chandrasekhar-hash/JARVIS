import uuid
import json
import time
import re
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

    async def event_generator():
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

        accumulated_text = ""
        sentence_buffer = ""

        # Helper to synthesize a text chunk and return an SSE audio data payload
        async def synthesize_and_yield(text_segment: str):
            text_segment = text_segment.strip()
            print(f"DEBUG_LOG: [Backend] Generating TTS for sentence: '{text_segment}'")
            if text_segment:
                try:
                    engine = tts_manager.get_engine(TTS_ENGINE)
                    audio_data = await engine.synthesize(
                        text=text_segment,
                        voice=voice_gender,
                        language=tts_lang_key
                    )
                    audio_id = str(uuid.uuid4())
                    audio_cache.set(audio_id, audio_data)
                    return f"data: {json.dumps({'type': 'audio_url', 'url': f'/api/audio/{audio_id}', 'text': text_segment})}\n\n"
                except Exception as e:
                    return f"data: {json.dumps({'type': 'error', 'content': f'TTS synthesis failed: {str(e)}'})}\n\n"
            return None

        # 1. Stream the LLM response text chunk-by-chunk for live UI rendering
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
                        yield f"data: {json.dumps({'type': 'error', 'content': f'Groq API error status {response.status_code}'})}\n\n"
                        return

                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue
                        print(f"DEBUG_LOG: [Backend] Groq streamed line: {line[:50]}...")
                        if line == "data: [DONE]":
                            break
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                token = data["choices"][0]["delta"].get("content", "")
                                if token:
                                    accumulated_text += token
                                    sentence_buffer += token
                                    yield f"data: {json.dumps({'type': 'text', 'content': token})}\n\n"
                                    
                                    # Check for complete sentences followed by space
                                    while True:
                                        match = re.search(r'(.*?[.!?]+)\s+', sentence_buffer)
                                        if match:
                                            sentence = match.group(1).strip()
                                            if len(sentence) >= 3:
                                                audio_event = await synthesize_and_yield(sentence)
                                                if audio_event:
                                                    yield audio_event
                                            sentence_buffer = sentence_buffer[match.end():]
                                        else:
                                            break
                            except Exception:
                                pass
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'content': f'Connection failed: {str(e)}'})}\n\n"
                return

        # 2. Synthesize audio for any final remainder text left in the sentence buffer
        final_sentence = sentence_buffer.strip()
        if len(final_sentence) >= 2:
            audio_event = await synthesize_and_yield(final_sentence)
            if audio_event:
                yield audio_event

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
