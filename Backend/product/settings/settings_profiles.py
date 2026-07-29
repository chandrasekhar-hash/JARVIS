"""
Configuration Profile Manager with Inheritance Resolution for Phase P1.3 (Settings & Configuration).
Supports parent-child profile inheritance (Default -> Coding, Meeting, Silent, Gaming).
Child profiles store ONLY overrides and inherit un-overridden settings from parent profiles.
"""
import uuid
import time
import logging
from typing import Optional, List, Dict, Any

from .settings_models import SettingProfile, SettingValue
from .settings_interfaces import ISettingsProfileManager, ISettingsRepository, ISettingsValidator

logger = logging.getLogger("JARVIS_SettingsProfileManager")


class SettingsProfileManager(ISettingsProfileManager):
    """
    Profile Manager handling configuration profiles and multi-level inheritance resolution.
    """

    def __init__(self, repository: ISettingsRepository, validator: ISettingsValidator):
        self.repository = repository
        self.validator = validator

    def ensure_default_profile(self, user_id: str) -> SettingProfile:
        """
        Ensures a default profile ('Default') exists for the user ID and is active.
        """
        active = self.repository.get_active_profile(user_id)
        if active:
            return active

        profiles = self.repository.list_profiles(user_id)
        if profiles:
            prof = profiles[0]
            prof.is_active = True
            return self.repository.update_profile(prof)

        # Create default profile
        now = time.time()
        def_prof = SettingProfile(
            profile_id=f"prof_def_{user_id}",
            user_id=user_id,
            parent_profile_id=None,
            name="Default",
            description="System Default Profile",
            is_active=True,
            is_default=True,
            created_at=now,
            updated_at=now,
        )
        return self.repository.create_profile(def_prof)

    def create_profile(
        self,
        user_id: str,
        name: str,
        description: str = "",
        parent_profile_id: Optional[str] = None,
    ) -> SettingProfile:
        """Creates a new child configuration profile inheriting from parent_profile_id."""
        def_prof = self.ensure_default_profile(user_id)
        parent_id = parent_profile_id or def_prof.profile_id

        prof_id = f"prof_{str(uuid.uuid4())}"
        now = time.time()

        profile = SettingProfile(
            profile_id=prof_id,
            user_id=user_id,
            parent_profile_id=parent_id,
            name=name,
            description=description,
            is_active=False,
            is_default=False,
            created_at=now,
            updated_at=now,
        )
        return self.repository.create_profile(profile)

    def get_active_profile(self, user_id: str) -> SettingProfile:
        """Retrieves active profile for user ID."""
        return self.ensure_default_profile(user_id)

    def switch_profile(self, user_id: str, profile_id: str) -> SettingProfile:
        """Switches active profile for user ID."""
        target = self.repository.get_profile(user_id, profile_id)
        if not target:
            raise ValueError(f"Profile '{profile_id}' not found for user '{user_id}'.")

        target.is_active = True
        updated = self.repository.update_profile(target)
        logger.info(f"[SettingsProfileManager] Switched active profile to '{updated.name}' ({updated.profile_id}) for user '{user_id}'.")
        return updated

    def duplicate_profile(self, user_id: str, profile_id: str, new_name: str) -> SettingProfile:
        """Duplicates an existing profile along with its setting overrides."""
        source = self.repository.get_profile(user_id, profile_id)
        if not source:
            raise ValueError(f"Profile '{profile_id}' not found for user '{user_id}'.")

        new_prof = self.create_profile(
            user_id=user_id,
            name=new_name,
            description=f"Duplicate of {source.name}",
            parent_profile_id=source.parent_profile_id,
        )

        # Copy overrides
        source_overrides = self.repository.list_setting_values(user_id, profile_id)
        now = time.time()
        for sv in source_overrides:
            new_sv = SettingValue(
                setting_id=f"set_{str(uuid.uuid4())}",
                user_id=user_id,
                profile_id=new_prof.profile_id,
                category=sv.category,
                key=sv.key,
                value=sv.value,
                is_override=True,
                created_at=now,
                updated_at=now,
            )
            self.repository.save_setting_value(new_sv)

        return new_prof

    def delete_profile(self, user_id: str, profile_id: str) -> bool:
        """Deletes a profile by ID (cannot delete default profile)."""
        active = self.get_active_profile(user_id)
        target = self.repository.get_profile(user_id, profile_id)
        if not target or target.is_default:
            return False

        # If deleting active profile, fallback to Default profile first
        if active and active.profile_id == profile_id:
            def_prof = self.ensure_default_profile(user_id)
            self.switch_profile(user_id, def_prof.profile_id)

        return self.repository.delete_profile(user_id, profile_id)

    def resolve_inherited_setting(self, user_id: str, key: str, profile_id: Optional[str] = None) -> Any:
        """
        Resolves setting value following inheritance chain:
        Target Profile Override -> Parent Profile Override -> Default Profile Override -> System Registry Default.
        """
        active_prof = self.get_active_profile(user_id)
        target_prof_id = profile_id or active_prof.profile_id

        # 1. Check target profile override
        sv = self.repository.get_setting_value(user_id, key, target_prof_id)
        if sv is not None:
            return sv.value

        # 2. Check parent profile hierarchy
        curr_prof = self.repository.get_profile(user_id, target_prof_id)
        visited_profiles = {target_prof_id}

        while curr_prof and curr_prof.parent_profile_id:
            parent_id = curr_prof.parent_profile_id
            if parent_id in visited_profiles:
                break  # Prevent circular inheritance loops
            visited_profiles.add(parent_id)

            parent_sv = self.repository.get_setting_value(user_id, key, parent_id)
            if parent_sv is not None:
                return parent_sv.value

            curr_prof = self.repository.get_profile(user_id, parent_id)

        # 3. Fallback to System Metadata Registry Default
        defn = self.validator.get_definition(key)
        if defn:
            return defn.default_value

        raise KeyError(f"Setting key '{key}' is neither defined in database nor in central metadata registry.")
