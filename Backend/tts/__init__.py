"""
J.A.R.V.I.S. Phase V1.4 Voice Output Engine (TTS) Subsystem Package.
"""
from .config import VoiceConfig, voice_config
from .models import (
    VoiceProfile,
    AudioChunk,
    TTSResult,
    PlaybackState,
    PlaybackSession,
)
from .interfaces import (
    ITextPreprocessor,
    ISentenceSegmenter,
    ITTSProvider,
    IAudioOutput,
    IAudioCache,
    IPlaybackEngine,
)
from .text_preprocessor import TextPreprocessor
from .sentence_segmenter import SentenceSegmenter
from .audio_cache import AudioCache
from .audio_outputs import (
    MockAudioOutput,
    DesktopSpeakerOutput,
    FileOutput,
    WebSocketOutput,
    MobileAudioOutput,
)
from .providers import (
    BaseTTSProvider,
    EdgeTTSProvider,
    OpenAITTSProvider,
    AzureTTSProvider,
    ElevenLabsProvider,
    MockTTSProvider,
    TTSProviderFactory,
    strip_ssml_tags,
)
from .playback_engine import PlaybackEngine
from .metrics import VoiceMetrics, voice_metrics
from .events import (
    SpeechSynthesisStarted,
    SpeechChunkGenerated,
    SpeechPlaybackStarted,
    SpeechPlaybackPaused,
    SpeechPlaybackResumed,
    SpeechPlaybackCompleted,
    SpeechPlaybackCancelled,
    SpeechPlaybackError,
)
from .engine import VoiceEngine, voice_engine

__all__ = [
    "VoiceConfig",
    "voice_config",
    "VoiceProfile",
    "AudioChunk",
    "TTSResult",
    "PlaybackState",
    "PlaybackSession",
    "ITextPreprocessor",
    "ISentenceSegmenter",
    "ITTSProvider",
    "IAudioOutput",
    "IAudioCache",
    "IPlaybackEngine",
    "TextPreprocessor",
    "SentenceSegmenter",
    "AudioCache",
    "MockAudioOutput",
    "DesktopSpeakerOutput",
    "FileOutput",
    "WebSocketOutput",
    "MobileAudioOutput",
    "BaseTTSProvider",
    "EdgeTTSProvider",
    "OpenAITTSProvider",
    "AzureTTSProvider",
    "ElevenLabsProvider",
    "MockTTSProvider",
    "TTSProviderFactory",
    "strip_ssml_tags",
    "PlaybackEngine",
    "VoiceMetrics",
    "voice_metrics",
    "SpeechSynthesisStarted",
    "SpeechChunkGenerated",
    "SpeechPlaybackStarted",
    "SpeechPlaybackPaused",
    "SpeechPlaybackResumed",
    "SpeechPlaybackCompleted",
    "SpeechPlaybackCancelled",
    "SpeechPlaybackError",
    "VoiceEngine",
    "voice_engine",
]
