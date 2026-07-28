import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from Cloud.routes.auth_routes import get_current_user
from Cloud.webhooks.service import webhook_service

logger = logging.getLogger("JARVIS_WebhookRoutes")

router = APIRouter(prefix="/api/v1/webhooks", tags=["Cloud Webhooks"])


class SubscriptionRequest(BaseModel):
    event_type: str
    target_url: str
    secret_token: str


@router.post("/subscriptions")
async def create_webhook_subscription(
    req: SubscriptionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    sub = webhook_service.register_subscription(
        user_id=current_user["user_id"],
        event_type=req.event_type,
        target_url=req.target_url,
        secret_token=req.secret_token
    )
    return {"status": "success", "subscription": sub}


@router.get("/subscriptions")
async def list_webhook_subscriptions(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    subs = webhook_service.list_subscriptions(current_user["user_id"])
    return {"status": "success", "subscriptions": subs}


@router.delete("/subscriptions/{subscription_id}")
async def revoke_webhook_subscription(
    subscription_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    success = webhook_service.revoke_subscription(subscription_id)
    if not success:
        raise HTTPException(status_code=404, detail="Subscription not found.")
    return {"status": "success", "message": "Subscription revoked."}
