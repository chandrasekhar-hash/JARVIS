import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import cloud_settings
from routes.auth_routes import router as auth_router
from routes.device_routes import router as device_router
from routes.identity_routes import router as identity_router
from routes.health_routes import router as health_router
from routes.websocket_routes import router as websocket_router
from websocket.heartbeat import heartbeat_monitor

app = FastAPI(
    title=cloud_settings.app_name,
    version="2.0.0",
    description="J.A.R.V.I.S. Cloud API Gateway & Synchronization Engine (Phase 8.3)",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include v1 REST & WS Route Routers
app.include_router(auth_router)
app.include_router(device_router)
app.include_router(identity_router)
app.include_router(health_router)
app.include_router(websocket_router)

@app.on_event("startup")
async def startup_event():
    heartbeat_monitor.start()

@app.on_event("shutdown")
async def shutdown_event():
    heartbeat_monitor.stop()

@app.get("/")
async def root():
    return {
        "service": cloud_settings.app_name,
        "version": app.version,
        "environment": cloud_settings.environment,
        "docs": "/docs",
        "health": "/api/v1/health",
        "websocket_endpoint": "ws://localhost:8001/ws/sync"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=cloud_settings.host,
        port=cloud_settings.port,
        reload=False
    )
