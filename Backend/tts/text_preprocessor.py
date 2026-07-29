"""
Text Preprocessing Engine for J.A.R.V.I.S. Phase V1.4 Voice Output Engine (TTS).
Normalizes numbers, currency, dates, times, acronyms, and URLs for natural speech synthesis.
"""
import re
from .interfaces import ITextPreprocessor


class TextPreprocessor(ITextPreprocessor):
    """
    Preprocesses raw text response before synthesis to optimize speech naturalness.
    Performs expansion of currency, percentages, acronyms, URLs, and date formats.
    """

    ACRONYMS = {
        "AI": "A.I.",
        "API": "A.P.I.",
        "URL": "U.R.L.",
        "TTS": "T.T.S.",
        "STT": "S.T.T.",
        "VAD": "V.A.D.",
        "UI": "U.I.",
        "UX": "U.X.",
        "IPC": "I.P.C.",
        "HTTP": "H.T.T.P.",
        "HTTPS": "H.T.T.P.S.",
        "REST": "R.E.S.T.",
        "SSE": "S.S.E.",
        "WS": "W.S.",
        "JSON": "J.S.O.N.",
        "HTML": "H.T.M.L.",
        "CSS": "C.S.S.",
        "SQL": "S.Q.L.",
        "CPU": "C.P.U.",
        "RAM": "R.A.M.",
        "OS": "O.S.",
        "ID": "I.D.",
    }

    def preprocess(self, text: str) -> str:
        if not text or not text.strip():
            return ""

        cleaned = text.strip()

        # 1. Clean URLs: "https://github.com/foo" -> "github link"
        cleaned = re.sub(
            r"https?://(?:www\.)?([\w\-\.]+)(?:/\S*)?",
            r"\1 link",
            cleaned,
            flags=re.IGNORECASE,
        )

        # 2. Currency expansion: "$100" -> "100 dollars", "$5.50" -> "5 dollars and 50 cents"
        cleaned = re.sub(r"\$(\d+)\.(\d{2})\b", r"\1 dollars and \2 cents", cleaned)
        cleaned = re.sub(r"\$(\d+)\b", r"\1 dollars", cleaned)
        cleaned = re.sub(r"€(\d+)\b", r"\1 euros", cleaned)
        cleaned = re.sub(r"£(\d+)\b", r"\1 pounds", cleaned)

        # 3. Percentage expansion: "50%" -> "50 percent"
        cleaned = re.sub(r"(\d+)%", r"\1 percent", cleaned)

        # 4. Acronym pronunciation formatting
        words = cleaned.split()
        formatted_words = []
        for word in words:
            # Strip trailing punctuation for matching
            strip_match = re.match(r"^([^\w]*)([\w]+)([^\w]*)$", word)
            if strip_match:
                prefix, core, suffix = strip_match.groups()
                if core in self.ACRONYMS:
                    formatted_words.append(f"{prefix}{self.ACRONYMS[core]}{suffix}")
                    continue
            formatted_words.append(word)

        cleaned = " ".join(formatted_words)

        # 5. Multiple whitespace cleanup
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return cleaned
