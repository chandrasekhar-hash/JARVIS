import edge_tts
from .base import BaseTTSEngine

class EdgeTTSEngine(BaseTTSEngine):
    # Mapping of languages and genders to MS Edge/Azure neural voices
    VOICE_MAP = {
        "english": {
            "female": "en-US-JennyNeural",
            "male": "en-US-GuyNeural"
        },
        "hindi": {
            "female": "hi-IN-SwaraNeural",
            "male": "hi-IN-MadhurNeural"
        },
        "hinglish": {
            # en-IN is optimized for English spoken with an Indian accent/cadence
            "female": "en-IN-NeerjaNeural",
            "male": "en-IN-PrabhatNeural"
        },
        "telugu": {
            "female": "te-IN-ShrutiNeural",
            "male": "te-IN-MohanNeural"
        },
        "tamil": {
            "female": "ta-IN-PallaviNeural",
            "male": "ta-IN-ValluvarNeural"
        },
        "odia": {
            "female": "or-IN-SubhasiniNeural",
            "male": "hi-IN-MadhurNeural"  # Hindi Male fallback as requested
        },
        "kannada": {
            "female": "kn-IN-SapnaNeural",
            "male": "kn-IN-GaganNeural"
        },
        "malayalam": {
            "female": "ml-IN-SobhanaNeural",
            "male": "ml-IN-MidhunNeural"
        },
        "bengali": {
            "female": "bn-IN-TanishaNeural",
            "male": "bn-IN-BashkarNeural"
        },
        "gujarati": {
            "female": "gu-IN-DhwaniNeural",
            "male": "gu-IN-NiranjanNeural"
        },
        "punjabi": {
            "female": "pa-IN-KaurNeural",
            "male": "pa-IN-AnoopNeural"
        },
        "marathi": {
            "female": "mr-IN-AarohiNeural",
            "male": "mr-IN-ManoharNeural"
        }
    }

    async def synthesize(self, text: str, voice: str, language: str) -> bytes:
        # Resolve voice gender and language (lowercase for robustness)
        lang_key = language.lower().strip()
        gender_key = voice.lower().strip()
        
        # Check if language is supported, default to english if not found
        if lang_key not in self.VOICE_MAP:
            lang_key = "english"
            
        # Get voice name, default to female if invalid gender
        voice_gender_map = self.VOICE_MAP.get(lang_key, self.VOICE_MAP["english"])
        voice_name = voice_gender_map.get(gender_key, voice_gender_map["female"])
        
        # Synthesize audio using edge-tts
        communicate = edge_tts.Communicate(text, voice_name)
        audio_data = b""
        
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
                
        return audio_data
