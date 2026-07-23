import time
from typing import Tuple
from pydantic import BaseModel
from memory.ingestion.capture import RawObservation


class ValidationResult(BaseModel):
    is_valid: bool
    reason: str = "ok"


class ObservationValidator:
    """
    Validates RawObservation instances to ensure required fields, content quality,
    sane timestamps, and supported sources before processing further in ingestion.
    """

    ALLOWED_SOURCES = {
        "conversation",
        "vision",
        "tool_execution",
        "desktop_event",
        "file",
        "user_action",
    }

    @classmethod
    def validate(cls, observation: RawObservation) -> ValidationResult:
        if not observation:
            return ValidationResult(is_valid=False, reason="Observation is None or empty.")

        # 1. Source Validation
        source_clean = observation.source.lower().strip()
        if source_clean not in cls.ALLOWED_SOURCES:
            return ValidationResult(
                is_valid=False,
                reason=f"Unsupported observation source '{observation.source}'. Allowed: {cls.ALLOWED_SOURCES}"
            )

        # 2. Content Length Validation
        content_clean = observation.content.strip()
        if len(content_clean) < 3:
            return ValidationResult(
                is_valid=False,
                reason=f"Observation content too short ({len(content_clean)} chars). Minimum required: 3 chars."
            )

        # 3. Timestamp Sanity Validation
        now = time.time()
        # Prevent future timestamps beyond 60s skew tolerance
        if observation.timestamp > now + 60.0:
            return ValidationResult(
                is_valid=False,
                reason=f"Timestamp skew error: Observation timestamp ({observation.timestamp}) is in the future."
            )
            
        # Prevent ancient timestamps before 2020
        if observation.timestamp < 1577836800.0:  # 2020-01-01 00:00:00 UTC
            return ValidationResult(
                is_valid=False,
                reason=f"Invalid timestamp ({observation.timestamp}): Timestamp is older than minimum threshold."
            )

        return ValidationResult(is_valid=True, reason="ok")
