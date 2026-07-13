from typing import Dict
from .base import BaseTTSEngine
from .edge_tts_engine import EdgeTTSEngine

class TTSEngineManager:
    def __init__(self):
        # Register available engines. Default is Microsoft Edge TTS.
        # Future engines like Azure, ElevenLabs, Kokoro, Piper can be added here easily.
        self._engines: Dict[str, BaseTTSEngine] = {
            "edge": EdgeTTSEngine(),
        }

    def get_engine(self, name: str) -> BaseTTSEngine:
        name_lower = name.lower().strip()
        if name_lower not in self._engines:
            # Gracefully fallback to 'edge'
            return self._engines["edge"]
        return self._engines[name_lower]

# Singleton instance
tts_manager = TTSEngineManager()
