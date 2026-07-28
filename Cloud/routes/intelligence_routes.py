import json
import base64
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from Cloud.routes.auth_routes import get_current_user
from Cloud.intelligence.offloader import remote_offloader
from Cloud.services.context_mesh_service import context_mesh_service
from Cloud.services.presence_service import presence_service
from Cloud.intelligence.remote_agent import remote_agent_service
from Cloud.services.job_orchestrator import job_orchestrator
from Cloud.services.notification_service import notification_service
from Cloud.repositories.device_repository import device_repo

logger = logging.getLogger("JARVIS_IntelligenceRoutes")

router = APIRouter(prefix="/api/v1/intelligence", tags=["Remote Intelligence"])


class InferenceRequest(BaseModel):
    prompt: str
    preferred_provider: Optional[str] = None
    system_instruction: Optional[str] = None


class ContextSnapshotRequest(BaseModel):
    device_id: str
    context_type: str
    data: Dict[str, Any]
    ttl_seconds: float = 300.0
    confidence: float = 1.0


class RemoteAgentExecuteRequest(BaseModel):
    origin_device_id: str
    target_device_id: str
    command_payload: Dict[str, Any]
    signature_base64: str


class PresenceUpdateRequest(BaseModel):
    device_id: str
    status: str
    capabilities: Optional[list] = None
    workload_score: float = 0.0


@router.post("/inference")
async def execute_inference(
    req: InferenceRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    x_trace_id: Optional[str] = Header(None)
):
    try:
        res = await remote_offloader.execute_remote_inference(
            prompt=req.prompt,
            preferred_provider=req.preferred_provider,
            system_instruction=req.system_instruction,
            trace_id=x_trace_id
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/inference/stream")
async def stream_inference(
    req: InferenceRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    x_trace_id: Optional[str] = Header(None)
):
    async def event_generator():
        try:
            async for token in remote_offloader.stream_remote_inference(
                prompt=req.prompt,
                preferred_provider=req.preferred_provider,
                system_instruction=req.system_instruction,
                trace_id=x_trace_id
            ):
                yield f"data: {json.dumps({'token': token})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/context/snapshot")
async def submit_context_snapshot(
    req: ContextSnapshotRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    snap = context_mesh_service.submit_snapshot(
        user_id=current_user["user_id"],
        device_id=req.device_id,
        context_type=req.context_type,
        data=req.data,
        ttl_seconds=req.ttl_seconds,
        confidence=req.confidence
    )
    return {"status": "success", "snapshot": snap.model_dump()}


@router.get("/context")
async def get_aggregated_context(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    formatted = context_mesh_service.get_formatted_context_header(current_user["user_id"])
    snapshots = context_mesh_service.get_valid_snapshots_for_user(current_user["user_id"])
    return {
        "user_id": current_user["user_id"],
        "formatted_prompt_header": formatted,
        "valid_snapshots_count": len(snapshots)
    }


@router.post("/agent/execute")
async def execute_remote_agent_command(
    req: RemoteAgentExecuteRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    dev = device_repo.get_device(req.origin_device_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Originating device not found.")

    try:
        sig_bytes = base64.b64decode(req.signature_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Base64 signature format.")

    verified = remote_agent_service.verify_remote_command_payload(
        command_payload=req.command_payload,
        public_key_pem=dev.public_key,
        signature_bytes=sig_bytes
    )

    if not verified:
        raise HTTPException(status_code=401, detail="Cryptographic signature or capability verification failed.")

    # Create job in JobOrchestrator
    job = job_orchestrator.create_job(
        user_id=current_user["user_id"],
        origin_device_id=req.origin_device_id,
        task_type="remote_agent_command",
        payload=req.command_payload,
        priority=9
    )

    return {"status": "accepted", "job_id": job.job_id, "trace_id": job.trace_id}


@router.post("/presence")
async def update_presence(
    req: PresenceUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    await presence_service.update_presence(
        device_id=req.device_id,
        user_id=current_user["user_id"],
        new_status=req.status,
        capabilities=req.capabilities,
        workload_score=req.workload_score
    )
    return {"status": "success", "presence": presence_service.get_presence(req.device_id)}


@router.get("/notifications")
async def get_notifications(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    notifs = notification_service.get_notifications(current_user["user_id"], unread_only=True)
    return {"user_id": current_user["user_id"], "notifications": notifs}


@router.get("/circuit_status")
async def get_circuit_status(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return remote_offloader.get_circuit_status()
