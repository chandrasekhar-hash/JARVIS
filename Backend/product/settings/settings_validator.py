"""
Central Setting Metadata Registry and Validation Engine for Phase P1.3 (Settings & Configuration).
Provides complete validation for data types, min/max ranges, allowed enum options, and requires_restart flags.
"""
import json
import logging
from typing import Optional, Dict, Any, List

from .settings_models import (
    SettingDefinition,
    SettingCategory,
    SettingDataType,
    ValidationResult,
    ThemeOption,
)
from .settings_interfaces import ISettingsValidator

logger = logging.getLogger("JARVIS_SettingsValidator")


# Central Metadata Registry defining all configurable settings across 8 categories
SETTINGS_REGISTRY: Dict[str, SettingDefinition] = {
    # 1. ASSISTANT
    "assistant.name": SettingDefinition(
        key="assistant.name",
        category=SettingCategory.ASSISTANT,
        data_type=SettingDataType.STRING,
        default_value="J.A.R.V.I.S.",
        description="Preferred assistant display name.",
    ),
    "assistant.wake_word": SettingDefinition(
        key="assistant.wake_word",
        category=SettingCategory.ASSISTANT,
        data_type=SettingDataType.STRING,
        default_value="JARVIS",
        description="Voice activation wake word.",
    ),
    "assistant.voice": SettingDefinition(
        key="assistant.voice",
        category=SettingCategory.ASSISTANT,
        data_type=SettingDataType.STRING,
        default_value="en-US-Neural",
        description="Voice output synthesizer voice ID.",
    ),
    "assistant.speech_speed": SettingDefinition(
        key="assistant.speech_speed",
        category=SettingCategory.ASSISTANT,
        data_type=SettingDataType.FLOAT,
        default_value=1.0,
        min_value=0.5,
        max_value=2.0,
        description="Speech synthesis playback speed.",
    ),
    "assistant.speech_volume": SettingDefinition(
        key="assistant.speech_volume",
        category=SettingCategory.ASSISTANT,
        data_type=SettingDataType.INT,
        default_value=80,
        min_value=0,
        max_value=100,
        description="Speech synthesis output volume.",
    ),
    "assistant.language": SettingDefinition(
        key="assistant.language",
        category=SettingCategory.ASSISTANT,
        data_type=SettingDataType.STRING,
        default_value="en-US",
        description="Primary language code.",
    ),
    "assistant.conversation_style": SettingDefinition(
        key="assistant.conversation_style",
        category=SettingCategory.ASSISTANT,
        data_type=SettingDataType.STRING,
        default_value="concise_professional",
        description="Conversation interaction style.",
    ),
    "assistant.ai_model": SettingDefinition(
        key="assistant.ai_model",
        category=SettingCategory.ASSISTANT,
        data_type=SettingDataType.STRING,
        default_value="gemini-2.5-flash",
        description="Primary AI model engine.",
    ),
    "assistant.response_length": SettingDefinition(
        key="assistant.response_length",
        category=SettingCategory.ASSISTANT,
        data_type=SettingDataType.STRING,
        default_value="balanced",
        description="Preferred AI response length.",
    ),
    "assistant.creativity": SettingDefinition(
        key="assistant.creativity",
        category=SettingCategory.ASSISTANT,
        data_type=SettingDataType.INT,
        default_value=70,
        min_value=0,
        max_value=100,
        description="AI generation temperature/creativity index (0-100).",
    ),
    "assistant.thinking_mode": SettingDefinition(
        key="assistant.thinking_mode",
        category=SettingCategory.ASSISTANT,
        data_type=SettingDataType.BOOL,
        default_value=True,
        description="Enable deep reasoning thinking mode.",
    ),

    # 2. MEMORY
    "memory.enabled": SettingDefinition(
        key="memory.enabled",
        category=SettingCategory.MEMORY,
        data_type=SettingDataType.BOOL,
        default_value=True,
        description="Enable memory persistence.",
    ),
    "memory.auto_summarize": SettingDefinition(
        key="memory.auto_summarize",
        category=SettingCategory.MEMORY,
        data_type=SettingDataType.BOOL,
        default_value=True,
        description="Auto-summarize conversation turns into memory.",
    ),
    "memory.working_memory_size": SettingDefinition(
        key="memory.working_memory_size",
        category=SettingCategory.MEMORY,
        data_type=SettingDataType.INT,
        default_value=10,
        min_value=1,
        max_value=50,
        description="Max working memory context items.",
    ),
    "memory.retention_policy": SettingDefinition(
        key="memory.retention_policy",
        category=SettingCategory.MEMORY,
        data_type=SettingDataType.ENUM,
        default_value="PERMANENT",
        allowed_values=["PERMANENT", "SESSION_ONLY", "THIRTY_DAYS", "NINETY_DAYS"],
        description="Default memory retention policy.",
    ),
    "memory.confidence_threshold": SettingDefinition(
        key="memory.confidence_threshold",
        category=SettingCategory.MEMORY,
        data_type=SettingDataType.FLOAT,
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Minimum confidence score threshold for memory retrieval.",
    ),
    "memory.knowledge_storage": SettingDefinition(
        key="memory.knowledge_storage",
        category=SettingCategory.MEMORY,
        data_type=SettingDataType.BOOL,
        default_value=True,
        description="Enable saving knowledge records.",
    ),

    # 3. VOICE
    "voice.input_device": SettingDefinition(
        key="voice.input_device",
        category=SettingCategory.VOICE,
        data_type=SettingDataType.STRING,
        default_value="default_mic",
        requires_restart=True,
        description="Audio capture input device.",
    ),
    "voice.output_device": SettingDefinition(
        key="voice.output_device",
        category=SettingCategory.VOICE,
        data_type=SettingDataType.STRING,
        default_value="default_speaker",
        requires_restart=True,
        description="Audio output playback device.",
    ),
    "voice.microphone_gain": SettingDefinition(
        key="voice.microphone_gain",
        category=SettingCategory.VOICE,
        data_type=SettingDataType.FLOAT,
        default_value=1.0,
        min_value=0.0,
        max_value=2.0,
        description="Microphone capture gain factor.",
    ),
    "voice.noise_suppression": SettingDefinition(
        key="voice.noise_suppression",
        category=SettingCategory.VOICE,
        data_type=SettingDataType.BOOL,
        default_value=True,
        description="Enable background noise suppression.",
    ),
    "voice.voice_activation": SettingDefinition(
        key="voice.voice_activation",
        category=SettingCategory.VOICE,
        data_type=SettingDataType.BOOL,
        default_value=True,
        description="Enable hands-free voice wake activation.",
    ),
    "voice.silence_timeout": SettingDefinition(
        key="voice.silence_timeout",
        category=SettingCategory.VOICE,
        data_type=SettingDataType.INT,
        default_value=5,
        min_value=1,
        max_value=60,
        description="Silence duration timeout in seconds before ending turn.",
    ),
    "voice.streaming": SettingDefinition(
        key="voice.streaming",
        category=SettingCategory.VOICE,
        data_type=SettingDataType.BOOL,
        default_value=True,
        description="Enable real-time audio streaming.",
    ),

    # 4. APPEARANCE
    "appearance.theme": SettingDefinition(
        key="appearance.theme",
        category=SettingCategory.APPEARANCE,
        data_type=SettingDataType.ENUM,
        default_value="DARK",
        allowed_values=["DARK", "LIGHT", "GLASSMORPHISM", "HIGH_CONTRAST", "SYSTEM"],
        description="UI theme aesthetic style.",
    ),
    "appearance.accent_color": SettingDefinition(
        key="appearance.accent_color",
        category=SettingCategory.APPEARANCE,
        data_type=SettingDataType.STRING,
        default_value="#4A90E2",
        description="Primary UI accent color hex code.",
    ),
    "appearance.font_scale": SettingDefinition(
        key="appearance.font_scale",
        category=SettingCategory.APPEARANCE,
        data_type=SettingDataType.FLOAT,
        default_value=1.0,
        min_value=0.5,
        max_value=2.0,
        description="UI typography scale factor.",
    ),
    "appearance.animations": SettingDefinition(
        key="appearance.animations",
        category=SettingCategory.APPEARANCE,
        data_type=SettingDataType.BOOL,
        default_value=True,
        description="Enable micro-animations and smooth motion transitions.",
    ),
    "appearance.transparency": SettingDefinition(
        key="appearance.transparency",
        category=SettingCategory.APPEARANCE,
        data_type=SettingDataType.FLOAT,
        default_value=0.8,
        min_value=0.0,
        max_value=1.0,
        description="Glassmorphism background opacity.",
    ),
    "appearance.window_behavior": SettingDefinition(
        key="appearance.window_behavior",
        category=SettingCategory.APPEARANCE,
        data_type=SettingDataType.STRING,
        default_value="normal",
        description="Window layout dock/float behavior.",
    ),

    # 5. NOTIFICATIONS
    "notifications.desktop_notifications": SettingDefinition(
        key="notifications.desktop_notifications",
        category=SettingCategory.NOTIFICATIONS,
        data_type=SettingDataType.BOOL,
        default_value=True,
        description="Enable OS desktop notifications.",
    ),
    "notifications.sound_alerts": SettingDefinition(
        key="notifications.sound_alerts",
        category=SettingCategory.NOTIFICATIONS,
        data_type=SettingDataType.BOOL,
        default_value=True,
        description="Enable audible notification chimes.",
    ),
    "notifications.reminder_behavior": SettingDefinition(
        key="notifications.reminder_behavior",
        category=SettingCategory.NOTIFICATIONS,
        data_type=SettingDataType.STRING,
        default_value="pop_up",
        description="Reminder notification popup style.",
    ),
    "notifications.priority_levels": SettingDefinition(
        key="notifications.priority_levels",
        category=SettingCategory.NOTIFICATIONS,
        data_type=SettingDataType.STRING,
        default_value="all",
        description="Notification priority filter level.",
    ),
    "notifications.quiet_hours": SettingDefinition(
        key="notifications.quiet_hours",
        category=SettingCategory.NOTIFICATIONS,
        data_type=SettingDataType.BOOL,
        default_value=False,
        description="Suppress non-critical notifications during quiet hours.",
    ),

    # 6. PRIVACY
    "privacy.telemetry": SettingDefinition(
        key="privacy.telemetry",
        category=SettingCategory.PRIVACY,
        data_type=SettingDataType.BOOL,
        default_value=False,
        description="Opt-in telemetry metrics collection.",
    ),
    "privacy.diagnostics": SettingDefinition(
        key="privacy.diagnostics",
        category=SettingCategory.PRIVACY,
        data_type=SettingDataType.BOOL,
        default_value=True,
        description="Enable local diagnostic crash logging.",
    ),
    "privacy.analytics": SettingDefinition(
        key="privacy.analytics",
        category=SettingCategory.PRIVACY,
        data_type=SettingDataType.BOOL,
        default_value=False,
        description="Opt-in usage analytics.",
    ),
    "privacy.memory_sharing": SettingDefinition(
        key="privacy.memory_sharing",
        category=SettingCategory.PRIVACY,
        data_type=SettingDataType.BOOL,
        default_value=False,
        description="Allow memory sharing across workspaces.",
    ),
    "privacy.export_permission": SettingDefinition(
        key="privacy.export_permission",
        category=SettingCategory.PRIVACY,
        data_type=SettingDataType.BOOL,
        default_value=True,
        description="Allow user data export.",
    ),
    "privacy.delete_permission": SettingDefinition(
        key="privacy.delete_permission",
        category=SettingCategory.PRIVACY,
        data_type=SettingDataType.BOOL,
        default_value=True,
        description="Allow hard deletion of user records.",
    ),
    "privacy.consent_version": SettingDefinition(
        key="privacy.consent_version",
        category=SettingCategory.PRIVACY,
        data_type=SettingDataType.INT,
        default_value=1,
        description="Accepted privacy policy version.",
    ),

    # 7. PERFORMANCE
    "performance.cache_limits_mb": SettingDefinition(
        key="performance.cache_limits_mb",
        category=SettingCategory.PERFORMANCE,
        data_type=SettingDataType.INT,
        default_value=512,
        min_value=10,
        max_value=10000,
        description="Max cache memory limit in megabytes.",
    ),
    "performance.worker_threads": SettingDefinition(
        key="performance.worker_threads",
        category=SettingCategory.PERFORMANCE,
        data_type=SettingDataType.INT,
        default_value=4,
        min_value=1,
        max_value=32,
        requires_restart=True,
        description="Parallel worker execution thread pool count.",
    ),
    "performance.logging_level": SettingDefinition(
        key="performance.logging_level",
        category=SettingCategory.PERFORMANCE,
        data_type=SettingDataType.ENUM,
        default_value="INFO",
        allowed_values=["DEBUG", "INFO", "WARNING", "ERROR"],
        description="Minimum log level cutoff.",
    ),
    "performance.network_timeout_sec": SettingDefinition(
        key="performance.network_timeout_sec",
        category=SettingCategory.PERFORMANCE,
        data_type=SettingDataType.INT,
        default_value=10,
        min_value=1,
        max_value=120,
        description="Network HTTP request timeout in seconds.",
    ),
    "performance.gpu_usage": SettingDefinition(
        key="performance.gpu_usage",
        category=SettingCategory.PERFORMANCE,
        data_type=SettingDataType.BOOL,
        default_value=True,
        requires_restart=True,
        description="Enable GPU hardware acceleration.",
    ),
    "performance.cpu_limits_pct": SettingDefinition(
        key="performance.cpu_limits_pct",
        category=SettingCategory.PERFORMANCE,
        data_type=SettingDataType.INT,
        default_value=80,
        min_value=10,
        max_value=100,
        description="Maximum CPU core utilization limit percentage.",
    ),

    # 8. DEVELOPER
    "developer.developer_mode": SettingDefinition(
        key="developer.developer_mode",
        category=SettingCategory.DEVELOPER,
        data_type=SettingDataType.BOOL,
        default_value=False,
        description="Enable developer tool inspect features.",
    ),
    "developer.debug_mode": SettingDefinition(
        key="developer.debug_mode",
        category=SettingCategory.DEVELOPER,
        data_type=SettingDataType.BOOL,
        default_value=False,
        description="Enable detailed debug log outputs.",
    ),
    "developer.verbose_logs": SettingDefinition(
        key="developer.verbose_logs",
        category=SettingCategory.DEVELOPER,
        data_type=SettingDataType.BOOL,
        default_value=False,
        description="Enable verbose audio/subsystem packet traces.",
    ),
    "developer.experimental_features": SettingDefinition(
        key="developer.experimental_features",
        category=SettingCategory.DEVELOPER,
        data_type=SettingDataType.BOOL,
        default_value=False,
        is_experimental=True,
        description="Enable experimental feature flags.",
    ),
    "developer.plugin_debugging": SettingDefinition(
        key="developer.plugin_debugging",
        category=SettingCategory.DEVELOPER,
        data_type=SettingDataType.BOOL,
        default_value=False,
        description="Enable live plugin reloading and sandbox logs.",
    ),
}


class SettingsValidator(ISettingsValidator):
    """
    Validates proposed setting values against the central metadata registry.
    Checks data type coercion, range bounds, enum membership, and read-only flags.
    """

    def __init__(self, registry: Optional[Dict[str, SettingDefinition]] = None):
        self.registry = registry or SETTINGS_REGISTRY

    def get_definition(self, key: str) -> Optional[SettingDefinition]:
        """Looks up registered definition for key."""
        return self.registry.get(key)

    def list_definitions(self, category: Optional[SettingCategory] = None) -> List[SettingDefinition]:
        """Lists definitions optionally filtered by category."""
        if category:
            cat_enum = SettingCategory(category) if not isinstance(category, SettingCategory) else category
            return [d for d in self.registry.values() if d.category == cat_enum]
        return list(self.registry.values())

    def validate_setting(self, key: str, value: Any) -> ValidationResult:
        """
        Validates value against registered constraints.
        Returns ValidationResult with sanitized value and requires_restart flag.
        """
        defn = self.get_definition(key)
        if not defn:
            return ValidationResult(
                valid=False,
                error_message=f"Unknown setting key '{key}'. Key is not defined in metadata registry.",
            )

        if defn.is_read_only:
            return ValidationResult(
                valid=False,
                error_message=f"Setting '{key}' is read-only and cannot be modified.",
            )

        # 1. Type Coercion & Check
        try:
            if defn.data_type == SettingDataType.BOOL:
                if isinstance(value, str):
                    sanitized = value.lower() in ("true", "1", "yes")
                else:
                    sanitized = bool(value)
            elif defn.data_type == SettingDataType.INT:
                sanitized = int(value)
            elif defn.data_type == SettingDataType.FLOAT:
                sanitized = float(value)
            elif defn.data_type == SettingDataType.STRING or defn.data_type == SettingDataType.ENUM:
                sanitized = str(value).strip()
                if not sanitized and (key.endswith("name") or key.endswith("wake_word")):
                    return ValidationResult(valid=False, error_message=f"Setting '{key}' cannot be empty.")
            elif defn.data_type == SettingDataType.JSON:
                if isinstance(value, str):
                    sanitized = json.loads(value)
                else:
                    sanitized = value
            else:
                sanitized = value
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            return ValidationResult(
                valid=False,
                error_message=f"Setting '{key}' value '{value}' cannot be coerced to type {defn.data_type.value}: {e}",
            )

        # 2. Min/Max Range Validation
        if defn.min_value is not None and sanitized < defn.min_value:
            return ValidationResult(
                valid=False,
                error_message=f"Setting '{key}' value {sanitized} is below minimum allowed value of {defn.min_value}.",
            )
        if defn.max_value is not None and sanitized > defn.max_value:
            return ValidationResult(
                valid=False,
                error_message=f"Setting '{key}' value {sanitized} exceeds maximum allowed value of {defn.max_value}.",
            )

        # 3. Enum Allowed Values Validation
        if defn.allowed_values is not None:
            if sanitized not in defn.allowed_values:
                return ValidationResult(
                    valid=False,
                    error_message=f"Setting '{key}' value '{sanitized}' is not in allowed enum options: {defn.allowed_values}.",
                )

        return ValidationResult(
            valid=True,
            requires_restart=defn.requires_restart,
            sanitized_value=sanitized,
        )
