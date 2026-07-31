"""
JARVIS Product 1.9 - Voice Logger.
Structured JSON logger for Voice Intelligence Layer events.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger("jarvis.voice")


class VoiceLogger:
    @staticmethod
    def log_event(
        event_name: str,
        session_id: str,
        owner_id: str,
        details: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
    ):
        log_payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": event_name,
            "session_id": session_id,
            "owner_id": owner_id,
            "duration_ms": duration_ms,
            "details": details or {},
        }
        logger.info(json.dumps(log_payload))


voice_logger = VoiceLogger()
