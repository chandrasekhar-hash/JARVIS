"""
User Preferences Manager Service for J.A.R.V.I.S. Product Layer (Phase P1.1).
Manages voice settings, wake word, assistant name, AI model preferences, languages, notifications, and privacy options.
"""
import time
import logging
from typing import Optional, Dict, Any

from .config import ProductConfig, product_config
from .models import (
    UserPreferences,
    VoiceSettings,
    NotificationSettings,
    PrivacySettings,
)
from .interfaces import IPreferenceRepository

logger = logging.getLogger("JARVIS_PreferenceManager")


class PreferenceManager:
    """
    User Preferences Management domain service.
    Handles persistence, updates, and default fallback generation for user preferences.
    """

    def __init__(
        self,
        repository: IPreferenceRepository,
        config: Optional[ProductConfig] = None,
    ):
        self.repository = repository
        self.config = config or product_config

    def create_default_preferences(self, user_id: str) -> UserPreferences:
        """Instantiates and persists default UserPreferences for a new user."""
        prefs = UserPreferences(
            user_id=user_id,
            voice_settings=VoiceSettings(
                voice_id=self.config.default_voice_id,
                speech_rate=self.config.default_speech_rate,
                speech_pitch=self.config.default_speech_pitch,
            ),
            wake_word=self.config.default_wake_word,
            assistant_name=self.config.default_assistant_name,
            preferred_ai_model=self.config.default_ai_model,
            preferred_language=self.config.default_language,
            notification_settings=NotificationSettings(
                mute_audio=self.config.default_mute_audio,
                audio_chimes=self.config.default_audio_chimes,
                os_popups=self.config.default_os_popups,
            ),
            privacy_settings=PrivacySettings(
                cloud_telemetry=self.config.default_cloud_telemetry,
                privacy_level=self.config.default_privacy_level,
            ),
            updated_at=time.time(),
        )
        return self.repository.create_preferences(prefs)

    def get_preferences(self, user_id: str) -> UserPreferences:
        """
        Retrieves UserPreferences by user ID.
        Creates default preferences if record does not yet exist.
        """
        prefs = self.repository.get_preferences_by_user_id(user_id)
        if not prefs:
            return self.create_default_preferences(user_id)
        return prefs

    def update_preferences(
        self,
        user_id: str,
        voice_settings: Optional[VoiceSettings] = None,
        wake_word: Optional[str] = None,
        assistant_name: Optional[str] = None,
        preferred_ai_model: Optional[str] = None,
        preferred_language: Optional[str] = None,
        notification_settings: Optional[NotificationSettings] = None,
        privacy_settings: Optional[PrivacySettings] = None,
    ) -> UserPreferences:
        """Updates specific preferences fields."""
        prefs = self.get_preferences(user_id)

        if voice_settings is not None:
            prefs.voice_settings = voice_settings
        if wake_word is not None and wake_word.strip():
            prefs.wake_word = wake_word.strip()
        if assistant_name is not None and assistant_name.strip():
            prefs.assistant_name = assistant_name.strip()
        if preferred_ai_model is not None and preferred_ai_model.strip():
            prefs.preferred_ai_model = preferred_ai_model.strip()
        if preferred_language is not None and preferred_language.strip():
            prefs.preferred_language = preferred_language.strip()
        if notification_settings is not None:
            prefs.notification_settings = notification_settings
        if privacy_settings is not None:
            prefs.privacy_settings = privacy_settings

        prefs.updated_at = time.time()
        return self.repository.update_preferences(prefs)

    def update_voice_settings(
        self,
        user_id: str,
        voice_id: Optional[str] = None,
        speech_rate: Optional[float] = None,
        speech_pitch: Optional[float] = None,
    ) -> UserPreferences:
        """Updates voice synthesis parameters."""
        prefs = self.get_preferences(user_id)
        if voice_id is not None:
            prefs.voice_settings.voice_id = voice_id
        if speech_rate is not None:
            prefs.voice_settings.speech_rate = speech_rate
        if speech_pitch is not None:
            prefs.voice_settings.speech_pitch = speech_pitch

        return self.repository.update_preferences(prefs)

    def update_wake_word(self, user_id: str, wake_word: str) -> UserPreferences:
        """Updates user wake word preference."""
        if not wake_word or not wake_word.strip():
            raise ValueError("Wake word cannot be empty.")
        return self.update_preferences(user_id, wake_word=wake_word.strip())

    def update_assistant_name(self, user_id: str, assistant_name: str) -> UserPreferences:
        """Updates assistant persona name preference."""
        if not assistant_name or not assistant_name.strip():
            raise ValueError("Assistant name cannot be empty.")
        return self.update_preferences(user_id, assistant_name=assistant_name.strip())

    def delete_preferences(self, user_id: str) -> bool:
        """Deletes user preferences record."""
        return self.repository.delete_preferences(user_id)
