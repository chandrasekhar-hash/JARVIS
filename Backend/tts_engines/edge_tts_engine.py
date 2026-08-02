import edge_tts
from .base import BaseTTSEngine

class EdgeTTSEngine(BaseTTSEngine):
    # Mapping of languages and genders to MS Edge/Azure neural voices
    VOICE_MAP = {
        "english": {
            "female": "en-GB-SoniaNeural",
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

    async def synthesize(self, text: str, voice: str, language: str, rate: str = "-8%", pitch: str = "-2Hz") -> bytes:
        lang_key = language.lower().strip()
        gender_key = voice.strip()
        
        # If explicit neural voice identifier is provided (e.g. en-GB-SoniaNeural), use directly
        if "Neural" in gender_key or "-" in gender_key:
            voice_name = gender_key
        else:
            if lang_key not in self.VOICE_MAP:
                lang_key = "english"
            voice_gender_map = self.VOICE_MAP.get(lang_key, self.VOICE_MAP["english"])
            voice_name = voice_gender_map.get(gender_key.lower(), voice_gender_map["female"])
        
        # Synthesize audio using edge-tts with rate and pitch settings
        communicate = edge_tts.Communicate(text, voice_name, rate=rate, pitch=pitch)
        audio_data = b""
        
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
                
        return audio_data
