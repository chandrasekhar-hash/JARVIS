import time
import uuid
import secrets
import hashlib
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from Cloud.routes.auth_routes import get_current_user

logger = logging.getLogger("JARVIS_DeveloperRoutes")

router = APIRouter(prefix="/api/v1/developer", tags=["Cloud Developer Portal"])


class CreateAPIKeyRequest(BaseModel):
    name: str
    scopes: List[str] = ["read:memory", "write:tasks"]
    expires_in_days: Optional[int] = 365


class DeveloperKeyManager:
    def __init__(self):
        # key_id -> metadata
        self.keys: Dict[str, Dict[str, Any]] = {}

    def create_key(self, user_id: str, name: str, scopes: List[str], expires_in_days: Optional[int] = 365) -> Dict[str, Any]:
        key_id = f"key_{uuid.uuid4().hex[:12]}"
        raw_key = f"jrv_live_{secrets.token_urlsafe(24)}"
        key_prefix = raw_key[:12]
        key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

        now = time.time()
        expires_at = now + (expires_in_days * 86400) if expires_in_days else None

        item = {
            "key_id": key_id,
            "user_id": user_id,
            "api_key_hash": key_hash,
            "key_prefix": key_prefix,
            "name": name,
            "scopes": scopes,
            "status": "active",
            "created_at": now,
            "expires_at": expires_at
        }
        self.keys[key_id] = item
        logger.info(f"Created developer API key '{key_id}' ('{name}') with scopes {scopes}")
        return {"key_id": key_id, "api_key": raw_key, "metadata": item}

    def list_keys(self, user_id: str) -> List[Dict[str, Any]]:
        return [k for k in self.keys.values() if k["user_id"] == user_id]

    def revoke_key(self, key_id: str) -> bool:
        if key_id in self.keys:
            del self.keys[key_id]
            return True
        return False


developer_key_manager = DeveloperKeyManager()


@router.post("/keys")
async def create_developer_api_key(
    req: CreateAPIKeyRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    res = developer_key_manager.create_key(
        user_id=current_user["user_id"],
        name=req.name,
        scopes=req.scopes,
        expires_in_days=req.expires_in_days
    )
    return {"status": "success", "data": res}


@router.get("/keys")
async def list_developer_api_keys(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    keys = developer_key_manager.list_keys(current_user["user_id"])
    return {"status": "success", "keys": keys}


@router.delete("/keys/{key_id}")
async def revoke_developer_api_key(
    key_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    success = developer_key_manager.revoke_key(key_id)
    if not success:
        raise HTTPException(status_code=404, detail="Key not found.")
    return {"status": "success", "message": "API key revoked."}
