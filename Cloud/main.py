import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import cloud_settings
from routes.auth_routes import router as auth_router
from routes.device_routes import router as device_router
from routes.identity_routes import router as identity_router
from routes.health_routes import router as health_router
from routes.websocket_routes import router as websocket_router
from routes.intelligence_routes import router as intelligence_router
from routes.marketplace_routes import router as marketplace_router
from routes.webhook_routes import router as webhook_router
from routes.developer_routes import router as developer_router
from websocket.heartbeat import heartbeat_monitor

app = FastAPI(
    title=cloud_settings.app_name,
    version="3.0.0",
    description="J.A.R.V.I.S. Cloud API Gateway & Ecosystem Platform (Phase 9)",
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
app.include_router(intelligence_router)
app.include_router(marketplace_router)
app.include_router(webhook_router)
app.include_router(developer_router)

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
