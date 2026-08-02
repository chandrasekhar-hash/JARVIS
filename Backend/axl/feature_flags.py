import os
from typing import Dict, Any

class FeatureFlagEngine:
    def __init__(self):
        self._flags = {
            "ENABLE_VOICE": os.getenv("ENABLE_VOICE", "true").lower() == "true",
            "ENABLE_WORKSPACE": os.getenv("ENABLE_WORKSPACE", "true").lower() == "true",
            "ENABLE_AUTOMATION": os.getenv("ENABLE_AUTOMATION", "true").lower() == "true",
            "ENABLE_KNOWLEDGE": os.getenv("ENABLE_KNOWLEDGE", "true").lower() == "true",
            "ENABLE_REASONING": os.getenv("ENABLE_REASONING", "true").lower() == "true",
        }

    def is_enabled(self, flag_name: str) -> bool:
        return self._flags.get(flag_name, False)

    def get_all_flags(self) -> Dict[str, bool]:
        return dict(self._flags)

    def set_flag(self, flag_name: str, enabled: bool):
        self._flags[flag_name] = enabled

feature_flag_engine = FeatureFlagEngine()
