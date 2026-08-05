# J.A.R.V.I.S. I2.1 — Configuration & Management Guide

## 1. Overview

Configuration in J.A.R.V.I.S. is managed centrally via `backend/config.py` with environment variable overrides.

---

## 2. Configuration Parameters

| Parameter | Environment Variable | Default Value | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | `GEMINI_API_KEY` | None | Primary Google Gemini Vision & LLM API key |
| `GROQ_API_KEY` | `GROQ_API_KEY` | None | Groq API key for fast inference |
| `PORT` | `PORT` | `8000` | Backend API server port |
| `HOST` | `HOST` | `0.0.0.0` | Server binding IP address |
| `CORS_ORIGINS` | `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Allowed CORS origins |
| `TTS_ENGINE` | `TTS_ENGINE` | `edge` | Primary text-to-speech engine |
| `MAX_IMAGES_PER_REQUEST` | N/A | `5` | Maximum images per multi-image request |
| `MAX_IMAGE_SIZE_BYTES` | N/A | `10485760` (10MB) | Maximum file upload size limit |
| `SESSION_TIMEOUT_SECONDS` | N/A | `300` (5 min) | Ephemeral RAM context timeout |
| `SCENE_CHANGE_THRESHOLD` | N/A | `0.05` | 32x32 MSE threshold for scene change |

---

## 3. Database Schema Configuration (`logs/jarvis_memory.db`)

Tables managed automatically via SQLite:
1. `users`: User identity & password hashes
2. `sessions`: User auth session tokens
3. `identity_security`: Auth audit logs & keystore entries
4. `scheduler_jobs`: Autonomous background tasks

---

## 4. Keystore Configuration

Secrets (JWT keys, provider API keys) are encrypted locally using `MacOSKeychain`, `WindowsDPAPI`, `LinuxSecretService`, or fallback `EncryptedFileKeyStore`.
