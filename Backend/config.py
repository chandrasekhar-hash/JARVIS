import os
from pathlib import Path
from dotenv import load_dotenv

# Try to load from frontend .env first, then fallback to current folder or system env
frontend_env_path = Path(__file__).resolve().parents[1] / 'frontend' / '.env'
if frontend_env_path.exists():
    load_dotenv(dotenv_path=frontend_env_path)
else:
    load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY") or os.getenv("VITE_GROQ_API_KEY")
ACTIVE_PROVIDER = os.getenv("ACTIVE_PROVIDER", "groq")
ROUTING_MODE = os.getenv("ROUTING_MODE", "manual") # manual | auto | fallback
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("VITE_GEMINI_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
CEREBRAS_MODEL = os.getenv("CEREBRAS_MODEL", "gemma-4-31b")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")
TTS_ENGINE = os.getenv("TTS_ENGINE", "edge")
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")

