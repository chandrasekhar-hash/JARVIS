"""
Centralized Configuration for J.A.R.V.I.S. Product Layer (Phase P1.1).
Defines operational defaults, security thresholds, session timeouts, and preference defaults.
"""
from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class ProductConfig:
    """
    Configuration parameters for Phase P1.1 Product Layer: Identity, User Management,
    Session Management, Security Controls, and User Preferences.
    """
    # Database Settings
    db_path: str = "logs/product_identity.db"
    enable_wal_mode: bool = True
    db_timeout_seconds: float = 10.0

    # Cryptography & Password Hashing Settings
    hash_algorithm: str = "sha256"
    hash_iterations: int = 100000
    salt_length_bytes: int = 16
    min_password_length: int = 8
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digits: bool = True
    require_special_char: bool = False

    # Security & Rate Limiting
    max_failed_login_attempts: int = 5
    account_lockout_seconds: int = 900  # 15 minutes
    rate_limit_max_attempts: int = 10
    rate_limit_window_seconds: int = 60
    token_entropy_bytes: int = 32

    # Session Management Settings
    session_timeout_seconds: int = 86400  # 24 hours
    remember_me_expiration_seconds: int = 2592000  # 30 days
    max_active_sessions_per_user: int = 10
    session_sliding_window: bool = True

    # Password Reset Settings
    reset_token_ttl_seconds: int = 3600  # 1 hour
    max_reset_requests_per_hour: int = 3

    # Default User Preferences
    default_wake_word: str = "JARVIS"
    default_assistant_name: str = "J.A.R.V.I.S."
    default_voice_id: str = "en-US-Neural"
    default_speech_rate: float = 1.0
    default_speech_pitch: float = 1.0
    default_ai_model: str = "gemini-2.5-flash"
    default_language: str = "en-US"
    default_time_zone: str = "UTC"
    default_theme: str = "dark"
    default_mute_audio: bool = False
    default_audio_chimes: bool = True
    default_os_popups: bool = True
    default_cloud_telemetry: bool = False
    default_privacy_level: str = "standard"

    def to_dict(self) -> Dict[str, Any]:
        """Converts configuration to a dictionary representation."""
        return {
            "db_path": self.db_path,
            "session_timeout_seconds": self.session_timeout_seconds,
            "remember_me_expiration_seconds": self.remember_me_expiration_seconds,
            "max_failed_login_attempts": self.max_failed_login_attempts,
            "account_lockout_seconds": self.account_lockout_seconds,
            "min_password_length": self.min_password_length,
            "default_wake_word": self.default_wake_word,
            "default_assistant_name": self.default_assistant_name,
            "default_voice_id": self.default_voice_id,
            "default_ai_model": self.default_ai_model,
            "default_language": self.default_language,
            "default_theme": self.default_theme,
        }


# Default singleton instance
product_config = ProductConfig()
