"""
Recovery Policy Engine for J.A.R.V.I.S. Phase V1.6 Voice Orchestrator.
Provides explicit policies: RetryPolicy, AbortPolicy, RestartPolicy, IgnorePolicy.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("JARVIS_RecoveryPolicyManager")


class RecoveryPolicy:
    """Base class for recovery policies."""
    name: str = "BasePolicy"

    def apply(self, context: Dict[str, Any]) -> str:
        return self.name


class RetryPolicy(RecoveryPolicy):
    name = "RetryPolicy"

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    def apply(self, context: Dict[str, Any]) -> str:
        retry_count = context.get("retry_count", 0)
        if retry_count < self.max_retries:
            logger.info(f"[RecoveryPolicy] Applying RetryPolicy (attempt {retry_count + 1}/{self.max_retries}).")
            return "retry"
        logger.warning(f"[RecoveryPolicy] Retry limit reached ({self.max_retries}). Aborting.")
        return "abort"


class AbortPolicy(RecoveryPolicy):
    name = "AbortPolicy"

    def apply(self, context: Dict[str, Any]) -> str:
        logger.info("[RecoveryPolicy] Applying AbortPolicy. Session terminating cleanly.")
        return "abort"


class RestartPolicy(RecoveryPolicy):
    name = "RestartPolicy"

    def apply(self, context: Dict[str, Any]) -> str:
        logger.info("[RecoveryPolicy] Applying RestartPolicy. Orchestrator restarting.")
        return "restart"


class IgnorePolicy(RecoveryPolicy):
    name = "IgnorePolicy"

    def apply(self, context: Dict[str, Any]) -> str:
        logger.info("[RecoveryPolicy] Applying IgnorePolicy. Continuing execution.")
        return "ignore"


class RecoveryPolicyManager:
    """Manages error recovery policies across voice orchestration failure scenarios."""

    def __init__(self):
        self.policies: Dict[str, RecoveryPolicy] = {
            "speech_recognition_failure": RetryPolicy(max_retries=2),
            "conversation_failure": RetryPolicy(max_retries=2),
            "tts_failure": RetryPolicy(max_retries=2),
            "audio_failure": IgnorePolicy(),
            "timeout": AbortPolicy(),
            "unexpected_exception": AbortPolicy(),
        }

    def evaluate(self, failure_type: str, context: Optional[Dict[str, Any]] = None) -> str:
        ctx = context or {}
        policy = self.policies.get(failure_type, AbortPolicy())
        return policy.apply(ctx)
