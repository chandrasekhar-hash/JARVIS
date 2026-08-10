import os
from pathlib import Path
from dotenv import load_dotenv

# Priority loading for backend environment configuration
backend_dir = Path(__file__).resolve().parent
project_root = backend_dir.parent
frontend_dir = project_root / 'frontend'

# Load in order: frontend .env -> root .env -> backend .env (so backend .env overrides)
if (frontend_dir / '.env').exists():
    load_dotenv(dotenv_path=frontend_dir / '.env')
if (project_root / '.env').exists():
    load_dotenv(dotenv_path=project_root / '.env', override=True)
if (backend_dir / '.env').exists():
    load_dotenv(dotenv_path=backend_dir / '.env', override=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY") or os.getenv("VITE_GROQ_API_KEY")
ACTIVE_PROVIDER = os.getenv("ACTIVE_PROVIDER", "groq")
ROUTING_MODE = os.getenv("ROUTING_MODE", "manual") # manual | auto | fallback
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("VITE_GEMINI_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
CEREBRAS_MODEL = os.getenv("CEREBRAS_MODEL", "gemma-4-31b")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
TTS_ENGINE = os.getenv("TTS_ENGINE", "edge")
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")
CORS_ORIGINS_RAW = os.getenv("CORS_ORIGINS", "*")
CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS_RAW.split(",") if origin.strip()]

# Web Search Intelligence Configuration (I2.2 V1)
WEB_SEARCH_PROVIDER = os.getenv("WEB_SEARCH_PROVIDER", "duckduckgo")
WEB_SEARCH_TIMEOUT_SECONDS = float(os.getenv("WEB_SEARCH_TIMEOUT_SECONDS", "10.0"))
WEB_SEARCH_MAX_RESULTS = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "10"))
WEB_SEARCH_ENABLED = os.getenv("WEB_SEARCH_ENABLED", "true").lower() in ("true", "1", "yes")

# Webpage Retrieval & Content Intelligence Configuration (I2.2 V2)
WEB_FETCH_ENABLED = os.getenv("WEB_FETCH_ENABLED", "true").lower() in ("true", "1", "yes")
WEB_FETCH_TIMEOUT_SECONDS = float(os.getenv("WEB_FETCH_TIMEOUT_SECONDS", "10.0"))
WEB_FETCH_MAX_BYTES = int(os.getenv("WEB_FETCH_MAX_BYTES", "3000000")) # ~3MB
WEB_FETCH_MAX_REDIRECTS = int(os.getenv("WEB_FETCH_MAX_REDIRECTS", "5"))
WEB_FETCH_MAX_PAGES = int(os.getenv("WEB_FETCH_MAX_PAGES", "3"))
WEB_FETCH_CONCURRENCY = int(os.getenv("WEB_FETCH_CONCURRENCY", "3"))
WEB_FETCH_CACHE_ENABLED = os.getenv("WEB_FETCH_CACHE_ENABLED", "true").lower() in ("true", "1", "yes")
WEB_FETCH_CACHE_TTL_SECONDS = int(os.getenv("WEB_FETCH_CACHE_TTL_SECONDS", "300"))


