import json
import time
import uuid
from typing import Optional, List, Dict, Any
from models.schemas import AuditLogEntry
from database.connection import db_manager

class AuditRepository:
    def log_event(
        self,
        event_type: str,
        action: str,
        status: str,
        user_id: Optional[str] = None,
        device_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditLogEntry:
        log_id = f"aud_{uuid.uuid4().hex[:16]}"
        timestamp = time.time()
        details_dict = details or {}

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cloud_audit_logs (log_id, event_type, user_id, device_id, action, status, details_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id,
                event_type,
                user_id,
                device_id,
                action,
                status,
                json.dumps(details_dict),
                timestamp
            ))
            conn.commit()

        return AuditLogEntry(
            log_id=log_id,
            event_type=event_type,
            user_id=user_id,
            device_id=device_id,
            action=action,
            status=status,
            details=details_dict,
            timestamp=timestamp
        )

    def get_recent_logs(self, limit: int = 50) -> List[AuditLogEntry]:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cloud_audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            logs = []
            for row in rows:
                logs.append(AuditLogEntry(
                    log_id=row["log_id"],
                    event_type=row["event_type"],
                    user_id=row["user_id"],
                    device_id=row["device_id"],
                    action=row["action"],
                    status=row["status"],
                    details=json.loads(row["details_json"]) if row["details_json"] else {},
                    timestamp=row["timestamp"]
                ))
            return logs

audit_repo = AuditRepository()
