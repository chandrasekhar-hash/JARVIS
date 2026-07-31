"""
JARVIS Product 1.7 - Automation Logger.
Structured JSON logger for Automation Engine workflows.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger("jarvis.automation")


class AutomationLogger:
    @staticmethod
    def log_event(
        event_name: str,
        user_id: str,
        workflow_id: str,
        run_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
    ):
        log_payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": event_name,
            "user_id": user_id,
            "workflow_id": workflow_id,
            "run_id": run_id,
            "duration_ms": duration_ms,
            "details": details or {},
        }
        logger.info(json.dumps(log_payload))


automation_logger = AutomationLogger()
