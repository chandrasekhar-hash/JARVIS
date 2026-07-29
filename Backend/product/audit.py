"""
Dedicated Security Audit Logger for J.A.R.V.I.S. Product Layer (Phase P1.1).
Provides append-only, tamper-evident security audit logging independent of system diagnostic telemetry.
"""
import time
import json
import uuid
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

from .interfaces import IAuditRepository
from .config import ProductConfig, product_config

logger = logging.getLogger("JARVIS_SecurityAuditLogger")


class AuditLevel(str, Enum):
    """Security audit event severity level."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AuditEvent(str, Enum):
    """Enumeration of security audit event types."""
    USER_REGISTERED = "USER_REGISTERED"
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    ACCOUNT_UNLOCKED = "ACCOUNT_UNLOCKED"
    LOGOUT = "LOGOUT"
    SESSION_CREATED = "SESSION_CREATED"
    SESSION_REVOKED = "SESSION_REVOKED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    PASSWORD_RESET_REQUESTED = "PASSWORD_RESET_REQUESTED"
    PASSWORD_RESET_COMPLETED = "PASSWORD_RESET_COMPLETED"
    PROFILE_UPDATED = "PROFILE_UPDATED"
    PREFERENCES_UPDATED = "PREFERENCES_UPDATED"
    PERMISSION_DENIED = "PERMISSION_DENIED"


@dataclass
class AuditEntry:
    """Security audit log record data structure."""
    audit_id: str
    timestamp: float
    user_id: Optional[str]
    session_id: Optional[str]
    event_type: str
    severity: str
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    result: str = "SUCCESS"  # SUCCESS or FAILURE
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes audit log entry to dictionary."""
        return {
            "audit_id": self.audit_id,
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "event_type": self.event_type,
            "severity": self.severity,
            "device_id": self.device_id,
            "ip_address": self.ip_address,
            "result": self.result,
            "metadata": self.metadata,
        }


class SecurityAuditLogger:
    """
    Dedicated Security Audit Logger.
    Appends security-critical events permanently through the abstract IAuditRepository.
    """

    def __init__(
        self,
        repository: IAuditRepository,
        config: Optional[ProductConfig] = None,
    ):
        self.repository = repository
        self.config = config or product_config

    def record_event(
        self,
        event_type: AuditEvent,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        severity: AuditLevel = AuditLevel.INFO,
        device_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        result: str = "SUCCESS",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        """
        Appends a new security audit event log to permanent storage.
        """
        audit_id = f"aud_{str(uuid.uuid4())}"
        now = time.time()
        entry = AuditEntry(
            audit_id=audit_id,
            timestamp=now,
            user_id=user_id,
            session_id=session_id,
            event_type=event_type.value if isinstance(event_type, AuditEvent) else str(event_type),
            severity=severity.value if isinstance(severity, AuditLevel) else str(severity),
            device_id=device_id,
            ip_address=ip_address,
            result=result,
            metadata=metadata or {},
        )

        try:
            self.repository.log_audit_entry(entry)
            logger.info(
                f"[SecurityAuditLogger] Recorded audit event '{entry.event_type}' for user '{user_id}' (Result: {result})."
            )
        except Exception as e:
            logger.error(f"[SecurityAuditLogger] Failed to write audit log entry: {e}")

        return entry

    def query_audit_logs(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """Queries security audit log entries for internal administration."""
        return self.repository.query_audit_logs(user_id=user_id, event_type=event_type, limit=limit)
