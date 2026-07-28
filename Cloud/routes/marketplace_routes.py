import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from Cloud.routes.auth_routes import get_current_user
from Cloud.marketplace.service import marketplace_service

logger = logging.getLogger("JARVIS_MarketplaceRoutes")

router = APIRouter(prefix="/api/v1/marketplace", tags=["Cloud Marketplace"])


class PublishPluginRequest(BaseModel):
    name: str
    version: str
    sdk_version: str = "1.0"
    api_version: str = "1"
    minimum_runtime: str = "1.0.0"
    category: str = "productivity"
    description: str
    capabilities: List[str] = []
    package_url: str
    signature_b64: str


@router.get("/plugins")
async def list_marketplace_plugins(
    query: Optional[str] = Query(None),
    category: Optional[str] = Query(None)
):
    plugins = marketplace_service.search_plugins(query=query, category=category)
    return {"status": "success", "count": len(plugins), "plugins": plugins}


@router.get("/plugins/{plugin_id}")
async def get_marketplace_plugin(plugin_id: str):
    p = marketplace_service.get_plugin(plugin_id)
    if not p:
        raise HTTPException(status_code=404, detail="Plugin not found.")
    return {"status": "success", "plugin": p}


@router.post("/publish")
async def publish_marketplace_plugin(
    req: PublishPluginRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    item = marketplace_service.publish_plugin(
        publisher_id=current_user["user_id"],
        name=req.name,
        version=req.version,
        sdk_version=req.sdk_version,
        api_version=req.api_version,
        minimum_runtime=req.minimum_runtime,
        category=req.category,
        description=req.description,
        capabilities=req.capabilities,
        package_url=req.package_url,
        signature_b64=req.signature_b64
    )
    return {"status": "success", "plugin": item}


@router.post("/plugins/{plugin_id}/install")
async def install_marketplace_plugin(
    plugin_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    p = marketplace_service.get_plugin(plugin_id)
    if not p:
        raise HTTPException(status_code=404, detail="Plugin not found.")

    marketplace_service.increment_download(plugin_id)
    return {"status": "success", "install_manifest": p}
