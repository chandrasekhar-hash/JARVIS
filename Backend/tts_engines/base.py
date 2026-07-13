from abc import ABC, abstractmethod

class BaseTTSEngine(ABC):
    @abstractmethod
    async def synthesize(self, text: str, voice: str, language: str) -> bytes:
        """
        Synthesizes text into speech audio.
        
        :param text: The text to be converted to speech.
        :param voice: The requested voice type/gender (e.g., 'male', 'female').
        :param language: The language/locale of the text (e.g., 'english', 'hindi', 'hinglish').
        :return: Binary audio data (typically MP3/WAV depending on engine).
        """
        pass
