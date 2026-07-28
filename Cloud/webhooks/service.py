import time
import uuid
import hmac
import hashlib
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("JARVIS_WebhookService")


class WebhookService:
    """
    WebhookService managing outbound event subscriptions, payload formatting under
    standard contract (event_id, trace_id, timestamp, version, producer, payload),
    HMAC-SHA256 signature calculation, and delivery logging.
    """

    def __init__(self):
        # subscription_id -> Dict[str, Any]
        self.subscriptions: Dict[str, Dict[str, Any]] = {}

    def register_subscription(self, user_id: str, event_type: str, target_url: str, secret_token: str) -> Dict[str, Any]:
        sub_id = f"sub_{uuid.uuid4().hex[:12]}"
        item = {
            "subscription_id": sub_id,
            "user_id": user_id,
            "event_type": event_type,
            "target_url": target_url,
            "secret_token": secret_token,
            "status": "active",
            "created_at": time.time()
        }
        self.subscriptions[sub_id] = item
        logger.info(f"Registered webhook subscription '{sub_id}' for event '{event_type}' -> '{target_url}'")
        return item

    def compute_hmac_signature(self, payload_bytes: bytes, secret_token: str) -> str:
        return hmac.new(secret_token.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    def create_event_envelope(
        self,
        event_type: str,
        producer: str,
        payload: Dict[str, Any],
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        return {
            "event_id": f"evt_{uuid.uuid4().hex[:12]}",
            "trace_id": trace_id or f"trc_evt_{uuid.uuid4().hex[:12]}",
            "event_type": event_type,
            "timestamp": time.time(),
            "version": "1.0",
            "producer": producer,
            "payload": payload
        }

    async def dispatch_event(self, user_id: str, event_type: str, payload: Dict[str, Any], trace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        envelope = self.create_event_envelope(event_type, "jarvis.cloud.webhooks", payload, trace_id)
        payload_bytes = json.dumps(envelope).encode("utf-8")
        dispatched = []

        for sub_id, sub in self.subscriptions.items():
            if sub["user_id"] == user_id and sub["event_type"] in [event_type, "*"] and sub["status"] == "active":
                sig = self.compute_hmac_signature(payload_bytes, sub["secret_token"])
                dispatched.append({
                    "subscription_id": sub_id,
                    "target_url": sub["target_url"],
                    "signature": f"sha256={sig}",
                    "envelope": envelope
                })
                logger.info(f"Dispatched webhook event '{envelope['event_id']}' to '{sub['target_url']}'")

        return dispatched

    def list_subscriptions(self, user_id: str) -> List[Dict[str, Any]]:
        return [s for s in self.subscriptions.values() if s["user_id"] == user_id]

    def revoke_subscription(self, subscription_id: str) -> bool:
        if subscription_id in self.subscriptions:
            del self.subscriptions[subscription_id]
            return True
        return False


webhook_service = WebhookService()
