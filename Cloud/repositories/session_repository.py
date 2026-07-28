import time
from typing import Optional, List
from models.schemas import CloudSession, SessionStatus
from database.connection import db_manager

class SessionRepository:
    def get_session(self, session_id: str) -> Optional[CloudSession]:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cloud_sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return CloudSession(
                session_id=row["session_id"],
                user_id=row["user_id"],
                device_id=row["device_id"],
                access_token=row["access_token"],
                refresh_token=row["refresh_token"],
                expires_at=row["expires_at"],
                refresh_expires_at=row["refresh_expires_at"],
                created_at=row["created_at"],
                status=SessionStatus(row["status"]),
                ip_address=row["ip_address"],
                user_agent=row["user_agent"]
            )

    def get_session_by_token(self, access_token: str) -> Optional[CloudSession]:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cloud_sessions WHERE access_token = ?", (access_token,))
            row = cursor.fetchone()
            if not row:
                return None
            return CloudSession(
                session_id=row["session_id"],
                user_id=row["user_id"],
                device_id=row["device_id"],
                access_token=row["access_token"],
                refresh_token=row["refresh_token"],
                expires_at=row["expires_at"],
                refresh_expires_at=row["refresh_expires_at"],
                created_at=row["created_at"],
                status=SessionStatus(row["status"]),
                ip_address=row["ip_address"],
                user_agent=row["user_agent"]
            )

    def get_session_by_refresh_token(self, refresh_token: str) -> Optional[CloudSession]:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cloud_sessions WHERE refresh_token = ?", (refresh_token,))
            row = cursor.fetchone()
            if not row:
                return None
            return CloudSession(
                session_id=row["session_id"],
                user_id=row["user_id"],
                device_id=row["device_id"],
                access_token=row["access_token"],
                refresh_token=row["refresh_token"],
                expires_at=row["expires_at"],
                refresh_expires_at=row["refresh_expires_at"],
                created_at=row["created_at"],
                status=SessionStatus(row["status"]),
                ip_address=row["ip_address"],
                user_agent=row["user_agent"]
            )

    def save_session(self, session: CloudSession) -> CloudSession:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cloud_sessions (
                    session_id, user_id, device_id, access_token, refresh_token,
                    expires_at, refresh_expires_at, created_at, status, ip_address, user_agent
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    access_token = excluded.access_token,
                    refresh_token = excluded.refresh_token,
                    expires_at = excluded.expires_at,
                    refresh_expires_at = excluded.refresh_expires_at,
                    status = excluded.status
            """, (
                session.session_id,
                session.user_id,
                session.device_id,
                session.access_token,
                session.refresh_token,
                session.expires_at,
                session.refresh_expires_at,
                session.created_at,
                session.status.value,
                session.ip_address,
                session.user_agent
            ))
            conn.commit()
        return session

    def update_session_status(self, session_id: str, new_status: SessionStatus) -> bool:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE cloud_sessions SET status = ? WHERE session_id = ?",
                (new_status.value, session_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def count_active_sessions(self) -> int:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            now = time.time()
            cursor.execute(
                "SELECT COUNT(*) as count FROM cloud_sessions WHERE status = 'active' AND expires_at > ?",
                (now,)
            )
            return cursor.fetchone()["count"]

session_repo = SessionRepository()
