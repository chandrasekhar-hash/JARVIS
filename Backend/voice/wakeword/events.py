import time
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class BaseWakeEvent(BaseModel):
    event_type: str
    timestamp: float = Field(default_factory=time.time)


class WakeWordDetectedEvent(BaseWakeEvent):
    event_type: str = "WakeWordDetected"
    keyword: str
    confidence: float
    duration_seconds: float
    decision: str = "ACTIVATE"


class WakeWordRejectedEvent(BaseWakeEvent):
    event_type: str = "WakeWordRejected"
    keyword: str
    confidence: float
    threshold: float
    reason: str = "ConfidenceTooLow"


class EngineStartedEvent(BaseWakeEvent):
    event_type: str = "EngineStarted"
    primary_keyword: str


class EngineStoppedEvent(BaseWakeEvent):
    event_type: str = "EngineStopped"
    reason: str = "CleanShutdown"


class MicrophoneDisconnectedEvent(BaseWakeEvent):
    event_type: str = "MicrophoneDisconnected"
    error: str


class EngineRecoveredEvent(BaseWakeEvent):
    event_type: str = "EngineRecovered"
    attempt: int
