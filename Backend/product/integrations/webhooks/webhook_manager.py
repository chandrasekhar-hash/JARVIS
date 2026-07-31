"""
JARVIS Product 1.8 - Webhook Manager.
Receives, verifies HMAC-SHA256 signatures, deduplicates, and normalizes external webhook payloads into WorkspaceEvent objects.
"""

import hmac
import hashlib
import json
import logging
from typing import Dict, Any, Optional
from ..interfaces import IWebhookManager
from ..models import WorkspaceEvent

logger = logging.getLogger(__name__)


class WebhookManager(IWebhookManager):
    def __init__(self):
        self._seen_event_hashes: set = set()

    def verify_hmac_signature(self, raw_payload: str, signature: str, secret_key: str) -> bool:
        if not signature or not secret_key:
            return True
        computed = hmac.new(secret_key.encode("utf-8"), raw_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, signature)

    def process_incoming_webhook(
        self,
        connector_id: str,
        raw_payload: str,
        signature_header: Optional[str] = None,
        secret_key: Optional[str] = None,
    ) -> Optional[WorkspaceEvent]:
        # 1. Verify HMAC Signature
        if secret_key and not self.verify_hmac_signature(raw_payload, signature_header or "", secret_key):
            logger.warning(f"Webhook signature verification failed for connector {connector_id}.")
            return None

        # 2. Deduplicate Event
        event_hash = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()
        if event_hash in self._seen_event_hashes:
            logger.info(f"Duplicate webhook event skipped for connector {connector_id}.")
            return None
        self._seen_event_hashes.add(event_hash)

        # 3. Normalize Payload into WorkspaceEvent
        try:
            payload_dict = json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload
        except Exception:
            payload_dict = {"raw": raw_payload}

        event_type = payload_dict.get("event_type", "webhook_received")
        provider = payload_dict.get("provider", "workspace")
        owner_id = payload_dict.get("owner_id", "system")

        import uuid
        return WorkspaceEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            connector_id=connector_id,
            provider=provider,
            owner_id=owner_id,
            event_type=event_type,
            capability_version=payload_dict.get("capability_version", "v1"),
            payload=payload_dict,
        )
