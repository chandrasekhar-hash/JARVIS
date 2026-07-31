"""
JARVIS Product 1.8 - Integration Logger.
Structured JSON logger for Workspace Integrations framework events.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger("jarvis.integrations")


class IntegrationLogger:
    @staticmethod
    def log_event(
        event_name: str,
        user_id: str,
        connector_id: str,
        provider: str,
        secret_ref: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
    ):
        log_payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": event_name,
            "user_id": user_id,
            "connector_id": connector_id,
            "provider": provider,
            "secret_ref": secret_ref,
            "duration_ms": duration_ms,
            "details": details or {},
        }
        logger.info(json.dumps(log_payload))


integration_logger = IntegrationLogger()
