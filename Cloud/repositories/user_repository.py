import json
import time
from typing import Optional, List
from models.schemas import CloudUser
from database.connection import db_manager

class UserRepository:
    def get_user(self, user_id: str) -> Optional[CloudUser]:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cloud_users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return CloudUser(
                user_id=row["user_id"],
                display_name=row["display_name"],
                email=row["email"],
                avatar_url=row["avatar_url"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                preferences=json.loads(row["preferences_json"]) if row["preferences_json"] else {}
            )

    def save_user(self, user: CloudUser) -> CloudUser:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cloud_users (user_id, display_name, email, avatar_url, created_at, updated_at, preferences_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    email = excluded.email,
                    avatar_url = excluded.avatar_url,
                    updated_at = excluded.updated_at,
                    preferences_json = excluded.preferences_json
            """, (
                user.user_id,
                user.display_name,
                user.email,
                user.avatar_url,
                user.created_at,
                user.updated_at,
                json.dumps(user.preferences)
            ))
            conn.commit()
        return user

    def count_users(self) -> int:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM cloud_users")
            return cursor.fetchone()["count"]

user_repo = UserRepository()
