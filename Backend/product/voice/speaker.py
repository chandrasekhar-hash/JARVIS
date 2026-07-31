"""
JARVIS Product 1.9 - Speaker Profile Manager.
Maps detected speaker audio features to active Product 1.1 SecurityContext user profiles.
"""

import logging
from typing import Dict, Optional
from .models import SpeakerProfile

logger = logging.getLogger(__name__)


class SpeakerProfileManager:
    def __init__(self):
        self._profiles: Dict[str, SpeakerProfile] = {}

    def register_profile(self, profile: SpeakerProfile) -> None:
        self._profiles[profile.owner_id] = profile

    def get_profile(self, owner_id: str) -> Optional[SpeakerProfile]:
        return self._profiles.get(owner_id)
