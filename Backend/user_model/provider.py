import time
from typing import Dict, List, Optional, Any
from user_model.models import (
    UserProfile,
    ActivityWindow,
    WorkflowAffinity,
    UserPreference,
    PreferenceType,
)
from user_model.profile_manager import ProfileManager
from user_model.preference_store import PreferenceStore
from tools.telemetry import log_structured, backend_log


class UserContextProvider:
    """
    Public User Context Provider exposing high-performance lookup interfaces for context engines.
    SLA Targets:
      - Preference Lookup: < 20 ms
      - Profile Lookup: < 100 ms
    """

    def __init__(
        self,
        profile_manager: Optional[ProfileManager] = None,
        preference_store: Optional[PreferenceStore] = None,
    ):
        self.profile_manager = profile_manager or ProfileManager()
        self.preference_store = preference_store or PreferenceStore()

    def get_user_profile(self, user_id: str = "default_user") -> UserProfile:
        """Retrieves or builds the complete UserProfile in < 100 ms."""
        start = time.perf_counter()
        profile = self.profile_manager.build_profile(user_id=user_id)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        if elapsed_ms > 100.0:
            log_structured(
                backend_log,
                "WARNING",
                f"[UserContextProvider] Profile lookup SLA threshold exceeded: {elapsed_ms:.2f} ms",
            )
        return profile

    def get_preferences(
        self, user_id: str = "default_user", category: Optional[str] = None
    ) -> Dict[str, Any]:
        """Retrieves consolidated key-value preferences in < 20 ms."""
        start = time.perf_counter()
        prefs = self.preference_store.list_preferences(user_id=user_id, category=category)
        res_dict: Dict[str, Any] = {p.key: p.value for p in prefs}
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        if elapsed_ms > 20.0:
            log_structured(
                backend_log,
                "WARNING",
                f"[UserContextProvider] Preference lookup SLA threshold exceeded: {elapsed_ms:.2f} ms",
            )
        return res_dict

    def get_activity_windows(self, user_id: str = "default_user") -> List[ActivityWindow]:
        """Retrieves top daily activity windows for user."""
        profile = self.get_user_profile(user_id)
        return profile.habit_profile.activity_windows

    def get_workflow_affinities(self, user_id: str = "default_user") -> List[WorkflowAffinity]:
        """Retrieves learned workflow affinities for user."""
        profile = self.get_user_profile(user_id)
        return profile.habit_profile.workflow_affinities

    def get_preferred_tools(self, user_id: str = "default_user") -> List[str]:
        """Retrieves ordered list of preferred tools."""
        profile = self.get_user_profile(user_id)
        return profile.habit_profile.top_tools


# Global provider singleton instance
user_context_provider = UserContextProvider()
