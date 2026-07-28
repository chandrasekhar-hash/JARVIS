class WakeWordError(Exception):
    """Base exception for Wake Word Intelligence Engine."""
    pass


class MicrophoneDisconnectedError(WakeWordError):
    """Raised when audio input device is disconnected or unavailable."""
    pass


class AudioPreprocessingError(WakeWordError):
    """Raised when audio frame processing fails."""
    pass


class DetectionEngineError(WakeWordError):
    """Raised when acoustic pattern matching fails."""
    pass
