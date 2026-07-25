import os
from typing import List, Set
from pydantic import BaseModel, Field, field_validator


class CognitiveConfig(BaseModel):
    """
    Configuration settings and feature flags for Phase 6 Cognitive Subsystem.
    Supports environment variable overrides with default safety boundaries.
    """
    # Feature Flags
    ENABLE_PRE_REASONING: bool = Field(
        default_factory=lambda: os.getenv("JARVIS_ENABLE_PRE_REASONING", "true").lower() in ("true", "1", "yes")
    )
    ENABLE_REFLECTION: bool = Field(
        default_factory=lambda: os.getenv("JARVIS_ENABLE_REFLECTION", "true").lower() in ("true", "1", "yes")
    )
    ENABLE_ADAPTIVE_REPLANNING: bool = Field(
        default_factory=lambda: os.getenv("JARVIS_ENABLE_ADAPTIVE_REPLANNING", "true").lower() in ("true", "1", "yes")
    )

    # Thresholds
    MIN_CONFIDENCE_THRESHOLD: float = Field(
        default_factory=lambda: float(os.getenv("JARVIS_MIN_CONFIDENCE_THRESHOLD", "0.60"))
    )
    MAX_CONCURRENT_GOALS: int = Field(
        default_factory=lambda: int(os.getenv("JARVIS_MAX_CONCURRENT_GOALS", "3"))
    )
    MAX_COGNITIVE_REPLANS: int = Field(
        default_factory=lambda: int(os.getenv("JARVIS_MAX_COGNITIVE_REPLANS", "3"))
    )
    EXPERIENCE_SEARCH_LIMIT: int = Field(
        default_factory=lambda: int(os.getenv("JARVIS_EXPERIENCE_SEARCH_LIMIT", "5"))
    )
    MAX_TASK_GRAPH_DEPTH: int = Field(
        default_factory=lambda: int(os.getenv("JARVIS_MAX_TASK_GRAPH_DEPTH", "10"))
    )
    MAX_TASK_RETRIES: int = Field(
        default_factory=lambda: int(os.getenv("JARVIS_MAX_TASK_RETRIES", "3"))
    )

    # Timeouts
    REASONING_TIMEOUT_SECONDS: float = Field(
        default_factory=lambda: float(os.getenv("JARVIS_REASONING_TIMEOUT_SECONDS", "15.0"))
    )
    REFLECTION_TIMEOUT_SECONDS: float = Field(
        default_factory=lambda: float(os.getenv("JARVIS_REFLECTION_TIMEOUT_SECONDS", "10.0"))
    )

    # Security & Policy Settings
    ALLOWED_SAFETY_TIERS: Set[str] = Field(
        default_factory=lambda: set(
            os.getenv("JARVIS_ALLOWED_SAFETY_TIERS", "SAFE,ASK_ONCE,ALWAYS_CONFIRM").split(",")
        )
    )
    RESTRICTED_PATH_PATTERNS: List[str] = Field(
        default_factory=lambda: [
            p.strip() for p in os.getenv("JARVIS_RESTRICTED_PATHS", "System32,Windows,etc/shadow,etc/passwd").split(",") if p.strip()
        ]
    )

    @field_validator("MIN_CONFIDENCE_THRESHOLD")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("MIN_CONFIDENCE_THRESHOLD must be between 0.0 and 1.0")
        return v

    @field_validator("MAX_CONCURRENT_GOALS", "MAX_COGNITIVE_REPLANS", "MAX_TASK_GRAPH_DEPTH", "EXPERIENCE_SEARCH_LIMIT")
    @classmethod
    def validate_positive_int(cls, v: int, info) -> int:
        if v <= 0:
            raise ValueError(f"{info.field_name} must be a positive integer greater than 0")
        return v


cognitive_config = CognitiveConfig()
