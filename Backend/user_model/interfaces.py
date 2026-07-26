from typing import Protocol, List, Optional, Dict, Any
from user_model.models import (
    UserPreference,
    PreferenceType,
    UserHabitProfile,
    UserProfile,
    UserConsent,
    PreferenceObservation,
    PreferenceUpdateResult,
    ActivityWindow,
    WorkflowAffinity,
)


class IPreferenceStore(Protocol):
    def record_preference(self, preference: UserPreference) -> PreferenceUpdateResult:
        ...

    def update_preference(
        self, user_id: str, key: str, value: Any, confidence: float
    ) -> PreferenceUpdateResult:
        ...

    def delete_preference(self, user_id: str, key: str) -> bool:
        ...

    def get_preference(self, user_id: str, key: str) -> Optional[UserPreference]:
        ...

    def list_preferences(
        self,
        user_id: str,
        category: Optional[str] = None,
        preference_type: Optional[PreferenceType] = None,
    ) -> List[UserPreference]:
        ...

    def merge_duplicate_preferences(self, user_id: str) -> int:
        ...

    def apply_confidence_decay(self, user_id: str, decay_rate: float = 0.02) -> int:
        ...


class IHabitAnalyzer(Protocol):
    def analyze_habits(
        self,
        user_id: str,
        observations: List[PreferenceObservation],
        tool_usages: List[Dict[str, Any]],
    ) -> UserHabitProfile:
        ...


class IProfileManager(Protocol):
    def build_profile(self, user_id: str) -> UserProfile:
        ...

    def update_consent(self, consent: UserConsent) -> UserConsent:
        ...

    def get_consent(self, user_id: str) -> UserConsent:
        ...

    def delete_user_data(self, user_id: str, scope: str = "all") -> bool:
        ...


class IUserContextProvider(Protocol):
    def get_user_profile(self, user_id: str) -> UserProfile:
        ...

    def get_preferences(
        self, user_id: str, category: Optional[str] = None
    ) -> Dict[str, Any]:
        ...

    def get_activity_windows(self, user_id: str) -> List[ActivityWindow]:
        ...

    def get_workflow_affinities(self, user_id: str) -> List[WorkflowAffinity]:
        ...

    def get_preferred_tools(self, user_id: str) -> List[str]:
        ...
