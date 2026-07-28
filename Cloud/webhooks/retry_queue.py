import time
import logging
from typing import Dict, Any, List

logger = logging.getLogger("JARVIS_WebhookRetryQueue")


class WebhookRetryQueue:
    """
    Webhook Retry Queue managing exponential backoff retries (1s, 5s, 30s, 5m)
    and Dead-Letter Queue (DLQ) for failed outbound webhook transmissions.
    """

    def __init__(self, max_retries: int = 4):
        self.max_retries = max_retries
        self.backoffs = [1.0, 5.0, 30.0, 300.0]
        self.dlq: List[Dict[str, Any]] = []

    def handle_failed_dispatch(self, subscription_id: str, event_payload: Dict[str, Any], attempt: int, error_msg: str) -> float:
        if attempt >= self.max_retries:
            logger.error(f"Webhook dispatch for '{subscription_id}' reached MAX retries ({self.max_retries}). Moving to Dead-Letter Queue (DLQ).")
            self.dlq.append({
                "subscription_id": subscription_id,
                "payload": event_payload,
                "attempts": attempt,
                "error": error_msg,
                "failed_at": time.time()
            })
            return -1.0

        delay = self.backoffs[min(attempt, len(self.backoffs) - 1)]
        logger.warning(f"Retrying webhook dispatch for '{subscription_id}' in {delay}s (Attempt #{attempt + 1})...")
        return delay


webhook_retry_queue = WebhookRetryQueue()
