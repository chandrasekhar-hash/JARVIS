from fastapi import Request, HTTPException, status
from services.security_service import security_service

def verify_token_header(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Bearer token"
        )
    token = auth_header.replace("Bearer ", "").strip()
    payload = security_service.validate_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session access token"
        )
    return payload["sub"]
