# J.A.R.V.I.S. I2.1 — Deployment & Production Guide

## 1. Environment Requirements

- **Operating System**: macOS 13+, Ubuntu 22.04 LTS+, or Debian 12
- **Python Runtime**: Python 3.11 - 3.14 (Virtualenv recommended)
- **Node.js Runtime**: Node.js 18+ & npm 9+
- **Database**: SQLite 3.35+ (`logs/jarvis_memory.db`)

---

## 2. Environment Configuration (.env)

Set the following environment variables prior to launch:

```bash
# Core AI API Keys
GEMINI_API_KEY="your-gemini-api-key"
GROQ_API_KEY="your-groq-api-key"

# Server Configuration
PORT=8000
HOST="0.0.0.0"
ENVIRONMENT="production"
CORS_ORIGINS="http://localhost:5173,http://localhost:3000"

# Security & Authentication
JWT_SECRET="your-256-bit-secure-random-jwt-secret"
SECURITY_KEY="your-keystore-encryption-key"

# Email Verification (Brevo)
BREVO_API_KEY="your-brevo-api-key"
SENDER_EMAIL="jarvis@yourdomain.com"
```

---

## 3. Production Deployment Commands

### Backend Production Launch (Uvicorn / Gunicorn)
```bash
cd backend
source ../.venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 --loop uvloop
```

### Frontend Production Build & Serve
```bash
cd frontend
npm run build
# Serve dist directory via Nginx, Caddy, or static host
```

---

## 4. Docker Production Containerization

### Build Production Docker Image
```bash
docker build -t jarvis-core:i2.1 .
```

### Run Container with Limits
```bash
docker run -d \
  --name jarvis-app \
  --cpus="2.0" \
  --memory="2g" \
  -p 8000:8000 \
  --env-file .env \
  jarvis-core:i2.1
```
