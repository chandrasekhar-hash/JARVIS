from fastapi import APIRouter, HTTPException, Depends, Request, status
from pydantic import BaseModel
from typing import Optional, Dict, Any
from services.identity_service import identity_service
from middleware.rate_limit import rate_limiter

router = APIRouter(prefix="/api/v1/identity", tags=["Cloud Identity Service"])

class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None

@router.get("/profile")
async def get_user_profile(user_id: str, request: Request):
    rate_limiter.check_rate_limit(request)
    user = identity_service.get_user_profile(user_id)
    if not user:
        # Auto-provision if not exists
        user = identity_service.get_or_create_user(user_id=user_id)
    return {"status": "success", "user_profile": user.model_dump()}

@router.put("/profile")
async def update_user_profile(user_id: str, req: UpdateProfileRequest, request: Request):
    rate_limiter.check_rate_limit(request)
    user = identity_service.update_user_profile(
        user_id=user_id,
        display_name=req.display_name,
        email=req.email,
        preferences=req.preferences
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found")
    return {"status": "success", "user_profile": user.model_dump()}
