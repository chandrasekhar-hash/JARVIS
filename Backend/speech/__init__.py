"""
J.A.R.V.I.S. Phase V1.2 Speech Recognition Engine Subsystem Package.
"""
from .config import SpeechConfig, speech_config
from .models import (
    AudioFrame,
    VADResult,
    STTResult,
    LanguageResult,
    EndpointResult,
    SpeechSession,
    SpeechState,
)
from .interfaces import (
    IAudioSource,
    IVADEngine,
    IStreamingSTTProvider,
    IEndpointDetector,
    ITranscriptBuffer,
    ILanguageDetector,
    ITranscriptCleaner,
    ISpeechRecoveryManager,
)
from .audio_sources import (
    MicrophoneSource,
    FileSource,
    WebSocketSource,
    MobileStreamSource,
)
from .vad import (
    EnergySpectralVADEngine,
    SileroVADEngine,
    WebRTCVADEngine,
    VADEngineFactory,
)
from .streaming_stt import (
    BaseStreamingSTTProvider,
    FasterWhisperProvider,
    GroqProvider,
    DeepgramProvider,
    OpenAIProvider,
    MockStreamingSTTProvider,
    STTProviderFactory,
)
from .transcript_buffer import TranscriptBuffer
from .language_detector import LanguageDetector
from .endpoint_detector import EndpointDetector
from .punctuation import TranscriptCleaner
from .recovery import SpeechRecoveryManager, logger as recovery_logger
from .metrics import SpeechMetrics, speech_metrics
from .events import (
    SpeechStartedEvent,
    SpeechPartialEvent,
    SpeechFinalEvent,
    SpeechEndedEvent,
    SpeechCancelledEvent,
    SpeechErrorEvent,
    LanguageDetectedEvent,
)
from .engine import SpeechRecognitionEngine, speech_engine

__all__ = [
    "SpeechConfig",
    "speech_config",
    "AudioFrame",
    "VADResult",
    "STTResult",
    "LanguageResult",
    "EndpointResult",
    "SpeechSession",
    "SpeechState",
    "IAudioSource",
    "IVADEngine",
    "IStreamingSTTProvider",
    "IEndpointDetector",
    "ITranscriptBuffer",
    "ILanguageDetector",
    "ITranscriptCleaner",
    "ISpeechRecoveryManager",
    "MicrophoneSource",
    "FileSource",
    "WebSocketSource",
    "MobileStreamSource",
    "EnergySpectralVADEngine",
    "SileroVADEngine",
    "WebRTCVADEngine",
    "VADEngineFactory",
    "BaseStreamingSTTProvider",
    "FasterWhisperProvider",
    "GroqProvider",
    "DeepgramProvider",
    "OpenAIProvider",
    "MockStreamingSTTProvider",
    "STTProviderFactory",
    "TranscriptBuffer",
    "LanguageDetector",
    "EndpointDetector",
    "TranscriptCleaner",
    "SpeechRecoveryManager",
    "SpeechMetrics",
    "speech_metrics",
    "SpeechStartedEvent",
    "SpeechPartialEvent",
    "SpeechFinalEvent",
    "SpeechEndedEvent",
    "SpeechCancelledEvent",
    "SpeechErrorEvent",
    "LanguageDetectedEvent",
    "SpeechRecognitionEngine",
    "speech_engine",
]
