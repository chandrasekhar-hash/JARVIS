"""
Structured Logger for J.A.R.V.I.S. Phase V1.8.
Provides context-aware structured JSON, console, and file logging with correlation IDs.
"""
import os
import json
import time
import logging
from typing import Optional, Dict, Any, List

from .config import DiagnosticsConfig, diagnostics_config
from .interfaces import ILogger
from .models import LogEntry

logger = logging.getLogger("JARVIS_StructuredLogger")


class StructuredLogger(ILogger):
    """
    Context-aware structured JSON & console logger.
    """

    def __init__(self, config: Optional[DiagnosticsConfig] = None):
        self.config = config or diagnostics_config
        self._history: List[LogEntry] = []
        self._capacity: int = 1000

        # Ensure log directory exists if file logging is enabled
        if self.config.enable_file_logging:
            log_dir = os.path.dirname(self.config.log_file_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

    def log(self, level: str, subsystem: str, message: str, correlation_id: str = "", **kwargs) -> None:
        entry = LogEntry(
            timestamp=time.time(),
            level=level.upper(),
            subsystem=subsystem,
            message=message,
            correlation_id=correlation_id,
            context=kwargs,
        )

        self._history.append(entry)
        if len(self._history) > self._capacity:
            self._history.pop(0)

        log_payload = {
            "timestamp": round(entry.timestamp, 3),
            "level": entry.level,
            "subsystem": entry.subsystem,
            "correlation_id": entry.correlation_id,
            "message": entry.message,
            "context": entry.context,
        }

        json_str = json.dumps(log_payload)

        # Output to Python logging system
        py_level = getattr(logging, entry.level, logging.INFO)
        logger.log(py_level, f"[{entry.subsystem}] {entry.message} (Correlation: {entry.correlation_id or 'none'})")

        # Output to file if enabled
        if self.config.enable_file_logging and self.config.log_file_path:
            try:
                with open(self.config.log_file_path, "a", encoding="utf-8") as f:
                    f.write(json_str + "\n")
            except Exception as e:
                logger.warning(f"[StructuredLogger] Failed to write log file: {e}")

    def debug(self, subsystem: str, message: str, correlation_id: str = "", **kwargs) -> None:
        self.log("DEBUG", subsystem, message, correlation_id, **kwargs)

    def info(self, subsystem: str, message: str, correlation_id: str = "", **kwargs) -> None:
        self.log("INFO", subsystem, message, correlation_id, **kwargs)

    def warning(self, subsystem: str, message: str, correlation_id: str = "", **kwargs) -> None:
        self.log("WARNING", subsystem, message, correlation_id, **kwargs)

    def error(self, subsystem: str, message: str, correlation_id: str = "", **kwargs) -> None:
        self.log("ERROR", subsystem, message, correlation_id, **kwargs)

    def critical(self, subsystem: str, message: str, correlation_id: str = "", **kwargs) -> None:
        self.log("CRITICAL", subsystem, message, correlation_id, **kwargs)

    def get_logs(self, limit: int = 100) -> List[LogEntry]:
        return self._history[-limit:]
