import logging
from typing import List, Dict, Set, Optional

logger = logging.getLogger("JARVIS_KeywordManager")


class KeywordManager:
    """
    Keyword Manager tracking primary wake word, active aliases, dynamic runtime updates,
    and case-insensitive keyword registration without requiring system restarts.
    """

    def __init__(
        self,
        primary_keyword: str = "jarvis",
        keywords: Optional[List[str]] = None,
        aliases: Optional[Dict[str, List[str]]] = None
    ):
        self.primary_keyword = primary_keyword.strip().lower()
        self._keywords: Set[str] = set()
        self._aliases: Dict[str, List[str]] = {}

        initial_words = keywords or ["jarvis", "hey jarvis", "computer", "nova", "friday"]
        for kw in initial_words:
            self.add_keyword(kw)

        if aliases:
            for primary, alias_list in aliases.items():
                for alias in alias_list:
                    self.add_alias(primary, alias)

    def add_keyword(self, keyword: str):
        kw_clean = keyword.strip().lower()
        if kw_clean:
            self._keywords.add(kw_clean)
            logger.info(f"Added wake word: '{kw_clean}'")

    def remove_keyword(self, keyword: str):
        kw_clean = keyword.strip().lower()
        if kw_clean in self._keywords and kw_clean != self.primary_keyword:
            self._keywords.remove(kw_clean)
            logger.info(f"Removed wake word: '{kw_clean}'")

    def add_alias(self, primary: str, alias: str):
        p_clean = primary.strip().lower()
        a_clean = alias.strip().lower()
        if p_clean and a_clean:
            self._aliases.setdefault(p_clean, []).append(a_clean)
            self._keywords.add(a_clean)
            logger.info(f"Added alias '{a_clean}' for primary wake word '{p_clean}'")

    def set_primary_keyword(self, keyword: str):
        kw_clean = keyword.strip().lower()
        if kw_clean:
            self.primary_keyword = kw_clean
            self.add_keyword(kw_clean)
            logger.info(f"Set primary wake word to: '{kw_clean}'")

    def get_all_keywords(self) -> List[str]:
        return sorted(list(self._keywords))

    def is_keyword_registered(self, keyword: str) -> bool:
        kw_clean = keyword.strip().lower()
        return kw_clean in self._keywords or any(kw_clean in aliases for aliases in self._aliases.values())


keyword_manager = KeywordManager()
