"""
User Profile Manager Service for J.A.R.V.I.S. Product Layer (Phase P1.1).
Manages metadata, avatars, regional formatting, theme preferences, and login metrics.
"""
import time
import logging
from typing import Optional, Dict, Any

from .models import UserProfile
from .interfaces import IProfileRepository

logger = logging.getLogger("JARVIS_ProfileManager")


class ProfileManager:
    """
    User Profile Management domain service.
    Handles creation, updates, and lookups of user profile records.
    """

    def __init__(self, repository: IProfileRepository):
        self.repository = repository

    def create_profile(
        self,
        user_id: str,
        username: str,
        display_name: str,
        email: str,
        avatar: str = "",
        language_preference: str = "en-US",
        time_zone: str = "UTC",
        theme_preference: str = "dark",
    ) -> UserProfile:
        """Creates initial UserProfile entity."""
        now = time.time()
        profile = UserProfile(
            user_id=user_id,
            username=username,
            display_name=display_name or username,
            email=email,
            avatar=avatar,
            language_preference=language_preference,
            time_zone=time_zone,
            theme_preference=theme_preference,
            account_creation_date=now,
            last_login=now,
        )
        return self.repository.create_profile(profile)

    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Fetches UserProfile by user ID."""
        return self.repository.get_profile_by_user_id(user_id)

    def update_profile(
        self,
        user_id: str,
        display_name: Optional[str] = None,
        email: Optional[str] = None,
        avatar: Optional[str] = None,
        language_preference: Optional[str] = None,
        time_zone: Optional[str] = None,
        theme_preference: Optional[str] = None,
    ) -> UserProfile:
        """Updates fields of an existing user profile."""
        profile = self.repository.get_profile_by_user_id(user_id)
        if not profile:
            raise ValueError(f"Profile for user_id '{user_id}' not found.")

        if display_name is not None:
            profile.display_name = display_name
        if email is not None:
            profile.email = email
        if avatar is not None:
            profile.avatar = avatar
        if language_preference is not None:
            profile.language_preference = language_preference
        if time_zone is not None:
            profile.time_zone = time_zone
        if theme_preference is not None:
            profile.theme_preference = theme_preference

        return self.repository.update_profile(profile)

    def record_login_timestamp(self, user_id: str, timestamp: Optional[float] = None) -> Optional[UserProfile]:
        """Updates last_login timestamp on profile."""
        profile = self.repository.get_profile_by_user_id(user_id)
        if not profile:
            return None

        profile.last_login = timestamp or time.time()
        return self.repository.update_profile(profile)

    def delete_profile(self, user_id: str) -> bool:
        """Deletes user profile record."""
        return self.repository.delete_profile(user_id)
