"""
JARVIS Product 1.6 - Knowledge Logger.
Structured JSON logger for Knowledge Engine operations.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger("jarvis.knowledge")


class KnowledgeLogger:
    @staticmethod
    def log_event(
        event_name: str,
        user_id: str,
        document_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
    ):
        log_payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": event_name,
            "user_id": user_id,
            "document_id": document_id,
            "duration_ms": duration_ms,
            "details": details or {},
        }
        logger.info(json.dumps(log_payload))


knowledge_logger = KnowledgeLogger()
