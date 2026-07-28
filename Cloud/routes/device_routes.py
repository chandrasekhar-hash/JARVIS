from fastapi import APIRouter, HTTPException, Depends, Request, status
from pydantic import BaseModel
from typing import Optional, List
from models.schemas import DeviceTrustState
from services.device_service import device_service
from services.identity_service import identity_service
from middleware.rate_limit import rate_limiter

router = APIRouter(prefix="/api/v1/devices", tags=["Cloud Device Service"])

class RegisterDeviceRequest(BaseModel):
    user_id: Optional[str] = None
    device_name: str
    platform: str
    architecture: str
    os_version: str
    public_key: str
    device_id: Optional[str] = None
    app_version: str = "1.0.0"

class UpdateTrustRequest(BaseModel):
    trust_state: DeviceTrustState

class RenameDeviceRequest(BaseModel):
    new_name: str

@router.post("/register")
async def register_device(req: RegisterDeviceRequest, request: Request):
    rate_limiter.check_rate_limit(request)
    # Ensure user identity exists
    user = identity_service.get_or_create_user(user_id=req.user_id)
    device = device_service.register_device(
        user_id=user.user_id,
        device_name=req.device_name,
        platform=req.platform,
        architecture=req.architecture,
        os_version=req.os_version,
        public_key=req.public_key,
        device_id=req.device_id,
        app_version=req.app_version
    )
    return {"status": "success", "device": device.model_dump()}

@router.get("/list")
async def list_user_devices(user_id: str, request: Request):
    rate_limiter.check_rate_limit(request)
    devices = device_service.list_user_devices(user_id)
    return {"status": "success", "devices": [d.model_dump() for d in devices]}

@router.get("/{device_id}")
async def get_device(device_id: str, request: Request):
    rate_limiter.check_rate_limit(request)
    device = device_service.get_device(device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return {"status": "success", "device": device.model_dump()}

@router.put("/{device_id}/trust")
async def update_device_trust(device_id: str, req: UpdateTrustRequest, request: Request):
    rate_limiter.check_rate_limit(request)
    success = device_service.update_device_trust(device_id, req.trust_state)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return {"status": "success", "message": f"Trust state updated to '{req.trust_state.value}'"}

@router.put("/{device_id}/rename")
async def rename_device(device_id: str, req: RenameDeviceRequest, request: Request):
    rate_limiter.check_rate_limit(request)
    success = device_service.rename_device(device_id, req.new_name)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return {"status": "success", "message": f"Device renamed to '{req.new_name}'"}

@router.delete("/{device_id}")
async def revoke_device(device_id: str, request: Request):
    rate_limiter.check_rate_limit(request)
    success = device_service.revoke_device(device_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return {"status": "success", "message": "Device trust revoked."}
