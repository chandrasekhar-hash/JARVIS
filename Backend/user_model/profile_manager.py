import time
from typing import Dict, List, Optional, Any
from user_model.models import (
    UserProfile,
    UserConsent,
    UserHabitProfile,
    UserPreference,
    PreferenceType,
    CommunicationStyle,
    PreferenceObservation,
)
from user_model.preference_store import PreferenceStore
from user_model.habit_analyzer import HabitAnalyzer
from brain.event_bus import event_bus, EventBus
from tools.telemetry import log_structured, backend_log


class ProfileManager:
    """
    Synthesizes explicit/implicit preferences, habit profiles, communication styles,
    and user consents into a unified, versioned UserProfile.
    Manages privacy state and data deletion requests.
    """

    def __init__(
        self,
        preference_store: Optional[PreferenceStore] = None,
        habit_analyzer: Optional[HabitAnalyzer] = None,
        bus: Optional[EventBus] = None,
    ):
        self.preference_store = preference_store or PreferenceStore()
        self.habit_analyzer = habit_analyzer or HabitAnalyzer()
        self.event_bus = bus or event_bus

        self._consent_store: Dict[str, UserConsent] = {}
        self._profile_cache: Dict[str, UserProfile] = {}

    def get_consent(self, user_id: str) -> UserConsent:
        if user_id not in self._consent_store:
            self._consent_store[user_id] = UserConsent(user_id=user_id)
        return self._consent_store[user_id]

    def update_consent(self, consent: UserConsent) -> UserConsent:
        consent.updated_at = time.time()
        self._consent_store[consent.user_id] = consent

        self.event_bus.emit(
            "ConsentChanged",
            user_id=consent.user_id,
            opt_in_personalization=consent.opt_in_personalization,
            implicit_learning_enabled=consent.implicit_learning_enabled,
        )

        log_structured(
            backend_log,
            "INFO",
            f"[ProfileManager] Updated consent for user '{consent.user_id}': opt_in={consent.opt_in_personalization}",
        )
        return consent

    def build_profile(
        self,
        user_id: str,
        observations: Optional[List[PreferenceObservation]] = None,
        tool_usages: Optional[List[Dict[str, Any]]] = None,
    ) -> UserProfile:
        consent = self.get_consent(user_id)
        if not consent.opt_in_personalization:
            # Personalization disabled -> return unpersonalized default profile
            return UserProfile(user_id=user_id, updated_at=time.time())

        # 1. Fetch preferences
        all_prefs = self.preference_store.list_preferences(user_id=user_id)
        explicit_dict: Dict[str, Any] = {}
        implicit_dict: Dict[str, Any] = {}

        for p in all_prefs:
            if p.preference_type == PreferenceType.EXPLICIT:
                explicit_dict[p.key] = p.value
            else:
                if consent.implicit_learning_enabled:
                    implicit_dict[p.key] = p.value

        # Conflict resolution: explicit overrides implicit
        for k in explicit_dict:
            if k in implicit_dict:
                del implicit_dict[k]

        # 2. Extract habit profile
        habit_profile = self.habit_analyzer.analyze_habits(
            user_id=user_id,
            observations=observations or [],
            tool_usages=tool_usages or [],
            consent=consent,
        )

        # 3. Determine preferred tools with affinity scores
        preferred_tools: Dict[str, float] = {}
        for tool in habit_profile.top_tools:
            preferred_tools[tool] = 0.8

        for h in habit_profile.habits:
            for t in h.associated_tools:
                preferred_tools[t] = max(preferred_tools.get(t, 0.5), h.confidence)

        # 4. Infer communication style
        comm_style = CommunicationStyle.CONCISE
        if "communication_style" in explicit_dict:
            try:
                comm_style = CommunicationStyle(str(explicit_dict["communication_style"]))
            except ValueError:
                comm_style = CommunicationStyle.CONCISE

        existing_profile = self._profile_cache.get(user_id)
        new_version = (existing_profile.profile_version + 1) if existing_profile else 1

        profile = UserProfile(
            user_id=user_id,
            communication_style=comm_style,
            preferred_tools=preferred_tools,
            explicit_preferences=explicit_dict,
            implicit_preferences=implicit_dict,
            habit_profile=habit_profile,
            profile_version=new_version,
            updated_at=time.time(),
        )

        self._profile_cache[user_id] = profile

        # Emit events
        self.event_bus.emit(
            "UserModelUpdated",
            user_id=user_id,
            profile_version=new_version,
            updated_at=profile.updated_at,
        )

        self.event_bus.emit(
            "HabitProfileUpdated",
            user_id=user_id,
            habits_count=len(habit_profile.habits),
            top_tools=habit_profile.top_tools,
        )

        log_structured(
            backend_log,
            "INFO",
            f"[ProfileManager] Built UserProfile (v{new_version}) for user '{user_id}' with {len(explicit_dict)} explicit prefs",
        )
        return profile

    def delete_user_data(self, user_id: str, scope: str = "all") -> bool:
        """Deletes user profile, preferences, or habits based on requested scope."""
        try:
            if scope in ["all", "preferences"]:
                self.preference_store.clear_all(user_id)
            if scope in ["all", "profile"]:
                if user_id in self._profile_cache:
                    del self._profile_cache[user_id]

            log_structured(
                backend_log,
                "INFO",
                f"[ProfileManager] Deleted user data scope='{scope}' for user '{user_id}'",
            )
            return True
        except Exception as e:
            log_structured(backend_log, "ERROR", f"[ProfileManager] Failed to delete user data: {str(e)}")
            return False
