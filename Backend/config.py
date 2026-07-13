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
TTS_ENGINE = os.getenv("TTS_ENGINE", "edge")
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")
