import time
import uuid
from typing import Optional, Dict, Any
from models.schemas import CloudUser
from repositories.user_repository import user_repo
from repositories.audit_repository import audit_repo

class IdentityService:
    def get_or_create_user(
        self,
        user_id: Optional[str] = None,
        display_name: str = "JARVIS Cloud User",
        email: Optional[str] = None
    ) -> CloudUser:
        if user_id:
            existing = user_repo.get_user(user_id)
            if existing:
                return existing

        new_id = user_id or f"usr_{uuid.uuid4().hex[:16]}"
        user = CloudUser(
            user_id=new_id,
            display_name=display_name,
            email=email,
            created_at=time.time(),
            updated_at=time.time(),
            preferences={"theme": "dark", "locale": "en-US", "ai_provider": "groq"}
        )
        saved = user_repo.save_user(user)
        audit_repo.log_event("USER_PROVISIONED", "provision_user", "success", user_id=new_id)
        return saved

    def get_user_profile(self, user_id: str) -> Optional[CloudUser]:
        return user_repo.get_user(user_id)

    def update_user_profile(
        self,
        user_id: str,
        display_name: Optional[str] = None,
        email: Optional[str] = None,
        preferences: Optional[Dict[str, Any]] = None
    ) -> Optional[CloudUser]:
        user = user_repo.get_user(user_id)
        if not user:
            return None

        if display_name:
            user.display_name = display_name
        if email is not None:
            user.email = email
        if preferences:
            user.preferences.update(preferences)

        user.updated_at = time.time()
        saved = user_repo.save_user(user)
        audit_repo.log_event("USER_UPDATED", "update_profile", "success", user_id=user_id)
        return saved

identity_service = IdentityService()
