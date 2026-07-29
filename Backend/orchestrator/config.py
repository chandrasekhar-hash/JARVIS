"""
Configuration Layer for J.A.R.V.I.S. Phase V1.6 Voice Orchestrator.
Centralized settings for barge-in, multi-turn timeouts, max session limits, parallel session policies,
recovery options, and logging telemetry.
"""
from dataclasses import dataclass, field


@dataclass
class OrchestratorConfig:
    """Centralized Voice Orchestrator Configuration."""
    enable_barge_in: bool = True
    enable_multi_turn: bool = True
    conversation_timeout_seconds: float = 60.0
    wake_timeout_seconds: float = 10.0
    listening_timeout_seconds: float = 15.0
    playback_timeout_seconds: float = 30.0
    idle_timeout_seconds: float = 300.0
    recovery_timeout_seconds: float = 10.0
    max_conversation_turns: int = 20
    max_sessions: int = 100
    allow_parallel_sessions: bool = True
    restart_on_failure: bool = True
    metrics_enabled: bool = True
    logging_enabled: bool = True


# Global default orchestrator configuration instance
orchestrator_config = OrchestratorConfig()
