from fastapi import APIRouter, HTTPException, Depends, Request, status
from pydantic import BaseModel
from typing import Optional
from services.security_service import security_service
from services.identity_service import identity_service
from middleware.rate_limit import rate_limiter

router = APIRouter(prefix="/api/v1/auth", tags=["Cloud Auth Service"])

class ChallengeRequest(BaseModel):
    device_id: str

class DeviceAuthRequest(BaseModel):
    device_id: str
    nonce: str
    signature_b64: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class RevokeSessionRequest(BaseModel):
    session_id: str

@router.post("/challenge")
async def create_auth_challenge(req: ChallengeRequest, request: Request):
    rate_limiter.check_rate_limit(request)
    challenge = security_service.create_auth_challenge(req.device_id)
    return {"status": "success", "challenge": challenge}

@router.post("/device-auth")
async def authenticate_device(req: DeviceAuthRequest, request: Request):
    rate_limiter.check_rate_limit(request)
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("User-Agent", "JARVIS Cloud Client")

    tokens = security_service.authenticate_device(
        device_id=req.device_id,
        nonce=req.nonce,
        signature_b64=req.signature_b64,
        ip_address=client_ip,
        user_agent=user_agent
    )
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed. Invalid Ed25519 signature or revoked device."
        )

    return {"status": "success", "tokens": tokens.model_dump()}

@router.post("/token/refresh")
async def refresh_access_token(req: RefreshTokenRequest, request: Request):
    rate_limiter.check_rate_limit(request)
    tokens = security_service.refresh_access_token(req.refresh_token)
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token."
        )
    return {"status": "success", "tokens": tokens.model_dump()}

@router.post("/token/revoke")
async def revoke_session(req: RevokeSessionRequest, request: Request):
    rate_limiter.check_rate_limit(request)
    success = security_service.revoke_session(req.session_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session not found or already revoked."
        )
    return {"status": "success", "message": "Session revoked successfully."}
