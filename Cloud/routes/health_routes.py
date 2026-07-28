from fastapi import APIRouter, Response, status
from services.telemetry_service import telemetry_service
from websocket.manager import ws_manager
from sync.crdt import crdt_engine
from sync.replay import replay_engine
from sync.redis_streams import redis_streams_bus

router = APIRouter(prefix="/api/v1", tags=["Cloud Observability & Health"])

@router.get("/health")
async def basic_health_check():
    return {
        "status": "healthy",
        "service": "JARVIS Cloud Platform API Gateway & Sync Engine",
        "active_ws_connections": len(ws_manager.active_connections)
    }

@router.get("/ready")
async def readiness_probe():
    security_status = telemetry_service.get_security_status()
    ws_state_counts = ws_manager.get_state_counts()
    queue_depth = redis_streams_bus.get_queue_depth() + replay_engine.get_offline_queue_depth()

    return {
        "status": "ready" if security_status.database_connected else "unready",
        "security_status": security_status.model_dump(),
        "websocket_gateway": {
            "active_connections": len(ws_manager.active_connections),
            "state_counts": ws_state_counts
        },
        "synchronization_engine": {
            "crdt_conflicts_resolved": crdt_engine.conflicts_count,
            "crdt_status": "operational",
            "replay_engine_status": "operational",
            "redis_streams_status": "connected" if redis_streams_bus.is_connected else "in_memory_fallback",
            "queue_depth": queue_depth
        }
    }

@router.get("/liveness")
async def liveness_probe():
    return {"status": "alive"}

@router.get("/security/status")
async def security_status():
    return {"status": "success", "security_status": telemetry_service.get_security_status().model_dump()}

@router.get("/metrics")
async def prometheus_metrics():
    metrics_data = telemetry_service.get_metrics_prometheus()
    return Response(content=metrics_data, media_type="text/plain; version=0.0.4; charset=utf-8")
