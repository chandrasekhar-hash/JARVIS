"""
JARVIS Product 1.9 - Recovery Manager.
Handles silence recovery prompts, ambiguous intent clarification, and audio hardware disconnect recovery.
"""

import logging

logger = logging.getLogger(__name__)


class RecoveryManager:
    def handle_silence_timeout(self, session_id: str) -> str:
        logger.info(f"[RecoveryManager] Silence timeout on session '{session_id}'. Generating polite recovery prompt.")
        return "I'm listening. How can I help you?"

    def handle_ambiguous_intent(self, transcript: str) -> str:
        logger.info(f"[RecoveryManager] Ambiguous transcript '{transcript}'. Requesting clarification turn.")
        return f"I didn't quite catch that. Did you want me to search the knowledge base or run a tool?"
