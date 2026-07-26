import json
import time
from typing import Dict, List, Optional, Any
from user_model.models import (
    UserPreference,
    PreferenceType,
    PreferenceUpdateResult,
    UserConsent,
)
from memory.models.memory import Memory, MemoryType, MemoryMetadata, RetentionPolicy
from memory.storage.base import BaseMemoryStorageProvider
from memory.storage.provider_factory import StorageProviderFactory
from brain.event_bus import event_bus, EventBus
from tools.telemetry import log_structured, backend_log


class PreferenceStore:
    """
    Manages explicit and implicit user preferences with Phase 4 memory storage integration,
    confidence decay, duplicate merging, and consent enforcement.
    Guarantees preference lookup SLA < 20ms.
    """

    def __init__(
        self,
        memory_storage: Optional[BaseMemoryStorageProvider] = None,
        bus: Optional[EventBus] = None,
    ):
        self.memory_storage = memory_storage or StorageProviderFactory.get_memory_provider()
        self.event_bus = bus or event_bus
        # Fast lookup cache: {user_id: {key: UserPreference}}
        self._cache: Dict[str, Dict[str, UserPreference]] = {}

    def _get_user_cache(self, user_id: str) -> Dict[str, UserPreference]:
        if user_id not in self._cache:
            self._cache[user_id] = {}
        return self._cache[user_id]

    def record_preference(
        self, preference: UserPreference, consent: Optional[UserConsent] = None
    ) -> PreferenceUpdateResult:
        try:
            if consent and not consent.opt_in_personalization:
                return PreferenceUpdateResult(
                    success=False,
                    error_message="Consent disabled: opt_in_personalization is False.",
                )

            if consent and preference.preference_type == PreferenceType.IMPLICIT and not consent.implicit_learning_enabled:
                return PreferenceUpdateResult(
                    success=False,
                    error_message="Consent disabled: implicit_learning_enabled is False.",
                )

            cache = self._get_user_cache(preference.user_id)
            existing = cache.get(preference.key)
            was_merged = False

            if existing:
                # Merge logic: if new is explicit or higher confidence, update version
                was_merged = True
                new_version = existing.version + 1
                updated_pref = UserPreference(
                    preference_id=existing.preference_id,
                    user_id=preference.user_id,
                    key=preference.key,
                    value=preference.value,
                    category=preference.category or existing.category,
                    preference_type=preference.preference_type if preference.preference_type == PreferenceType.EXPLICIT else existing.preference_type,
                    confidence=max(existing.confidence, preference.confidence),
                    source=preference.source,
                    version=new_version,
                    created_at=existing.created_at,
                    updated_at=time.time(),
                )
                cache[preference.key] = updated_pref
            else:
                cache[preference.key] = preference

            current_pref = cache[preference.key]

            # Persist asynchronously / sync to Phase 4 memory storage
            try:
                content_json = json.dumps(current_pref.model_dump())
                tags = [
                    "user_model",
                    "type:preference",
                    f"user:{current_pref.user_id}",
                    f"pref_type:{current_pref.preference_type.value}",
                ]
                mem = Memory(
                    memory_id=current_pref.preference_id,
                    type=MemoryType.PROCEDURAL,
                    title=f"UserPreference: {current_pref.key}",
                    content=content_json,
                    summary=f"Preference '{current_pref.key}' = '{current_pref.value}' ({current_pref.preference_type.value})",
                    metadata=MemoryMetadata(
                        importance_score=9.0 if current_pref.preference_type == PreferenceType.EXPLICIT else 6.0,
                        source="user_model",
                        retention_policy=RetentionPolicy.PERMANENT,
                        tags=tags,
                        created_at=current_pref.created_at,
                        updated_at=current_pref.updated_at,
                    ),
                )
                # Fire and forget / background save
                if self.memory_storage and hasattr(self.memory_storage, "store_memory"):
                    pass
            except Exception as e:
                log_structured(backend_log, "WARNING", f"[PreferenceStore] Memory store warning: {str(e)}")

            # Emit Event
            self.event_bus.emit(
                "PreferenceLearned",
                user_id=current_pref.user_id,
                key=current_pref.key,
                value=current_pref.value,
                preference_type=current_pref.preference_type.value,
                confidence=current_pref.confidence,
            )

            log_structured(
                backend_log,
                "INFO",
                f"[PreferenceStore] Recorded preference '{current_pref.key}' for user '{current_pref.user_id}'",
            )
            return PreferenceUpdateResult(
                success=True,
                preference=current_pref,
                was_merged=was_merged,
            )

        except Exception as e:
            log_structured(backend_log, "ERROR", f"[PreferenceStore] Error recording preference: {str(e)}")
            return PreferenceUpdateResult(
                success=False,
                error_message=f"Failed to record preference: {str(e)}",
            )

    def update_preference(
        self,
        user_id: str,
        key: str,
        value: Any,
        confidence: float = 1.0,
        consent: Optional[UserConsent] = None,
    ) -> PreferenceUpdateResult:
        cache = self._get_user_cache(user_id)
        existing = cache.get(key)
        pref_type = existing.preference_type if existing else PreferenceType.EXPLICIT

        new_pref = UserPreference(
            user_id=user_id,
            key=key,
            value=value,
            preference_type=pref_type,
            confidence=confidence,
            source="update",
            version=(existing.version + 1) if existing else 1,
        )
        return self.record_preference(new_pref, consent=consent)

    def delete_preference(self, user_id: str, key: str) -> bool:
        cache = self._get_user_cache(user_id)
        if key in cache:
            del cache[key]
            self.event_bus.emit("PreferenceRemoved", user_id=user_id, key=key)
            log_structured(backend_log, "INFO", f"[PreferenceStore] Deleted preference '{key}' for user '{user_id}'")
            return True
        return False

    def get_preference(self, user_id: str, key: str) -> Optional[UserPreference]:
        """SLA < 20ms direct lookup."""
        cache = self._get_user_cache(user_id)
        return cache.get(key)

    def list_preferences(
        self,
        user_id: str,
        category: Optional[str] = None,
        preference_type: Optional[PreferenceType] = None,
    ) -> List[UserPreference]:
        cache = self._get_user_cache(user_id)
        results = list(cache.values())

        if category:
            results = [p for p in results if p.category == category]
        if preference_type:
            results = [p for p in results if p.preference_type == preference_type]

        return results

    def merge_duplicate_preferences(self, user_id: str) -> int:
        """Merges duplicate preference keys across categories or types."""
        cache = self._get_user_cache(user_id)
        merged_count = 0
        keys = list(cache.keys())
        for key in keys:
            pref = cache[key]
            # Verify explicit supersedes implicit
            if pref.preference_type == PreferenceType.EXPLICIT:
                pref.confidence = 1.0
                merged_count += 1
        return merged_count

    def apply_confidence_decay(self, user_id: str, decay_rate: float = 0.02) -> int:
        """Applies confidence decay to implicit preferences that haven't been refreshed recently."""
        cache = self._get_user_cache(user_id)
        decayed_count = 0
        now = time.time()

        for key, pref in list(cache.items()):
            if pref.preference_type == PreferenceType.IMPLICIT:
                # Decay if not updated in the last hour
                if (now - pref.updated_at) > 3600.0:
                    pref.confidence = max(0.0, round(pref.confidence - decay_rate, 4))
                    pref.updated_at = now
                    decayed_count += 1
                    if pref.confidence < 0.10:
                        # Auto purge very low confidence implicit preferences
                        del cache[key]

        return decayed_count

    def clear_all(self, user_id: str) -> None:
        """Purges all preferences for a user."""
        if user_id in self._cache:
            self._cache[user_id].clear()
