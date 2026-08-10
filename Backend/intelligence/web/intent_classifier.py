"""
Web Needed Detector and Intent Classifier for J.A.R.V.I.S. I2.2 V1 Web Search Foundation.
Provides lightweight, deterministic, regex/pattern-based classification without LLM overhead.
"""
import re
from typing import Tuple
from intelligence.web.models import WebSearchIntent


class WebIntentClassifier:
    """
    Deterministic intent classifier & web-needed detector for J.A.R.V.I.S.
    Enforces clear boundaries between static conversational queries and queries requiring live web search.
    """

    def __init__(self):
        # Patterns for queries that strictly DO NOT require web search (static/conceptual/math)
        self._static_patterns = [
            r"^\s*what\s+is\s+(recursion|polymorphism|encapsulation|inheritance|abstraction|quicksort|mergesort|binary\s+search|a\s+closure|currying|a\s+pointer|a\s+mutex|a\s+deadlock|a\s+monad)\b",
            r"^\s*explain\s+(recursion|quicksort|mergesort|binary\s+search|the\s+difference\s+between\s+stack\s+and\s+heap|how\s+async/await\s+works)\b",
            r"^\s*write\s+a\s+(python|javascript|typescript|c\+\+|java|rust|go)\s+(function|script|program|class)\s+to\b",
            r"^\s*how\s+do\s+i\s+(reverse\s+a\s+string|sort\s+an\s+array|center\s+a\s+div|parse\s+json)\b",
            r"^\s*(calculate|compute|solve|eval|what\s+is)\s+\d+[\d\s\+\-\*\/\(\)\.]+$",
            r"^\s*who\s+wrote\s+(romeo\s+and\s+juliet|hamlet|macbeth|war\s+and\s+peace)\b",
            r"^\s*what\s+is\s+the\s+capital\s+of\s+(france|japan|germany|canada|italy|spain|india)\b",
        ]

        # Explicit keywords indicating live / temporal / external data is required
        self._web_keywords = [
            "latest", "today", "current", "recent", "news", "new",
            "release", "update", "version", "weather", "stock", "price",
            "documentation", "docs", "official", "changelog", "release notes",
            "announcement", "happened", "schedule", "scores", "event",
        ]

        # Explicit regex triggers for web search
        self._web_triggers = [
            r"\b(latest|current|recent|today|now)\b",
            r"\b(docs|documentation|official\s+site|official\s+website|homepage|download)\b",
            r"\b(release\s+notes|changelog|what\s+happened|news\s+on)\b",
            r"\b(version|pricing|price\s+of|stock\s+of|weather\s+in)\b",
            r"\b(gemini|gpt-4o|claude|react\s+19|python\s+3\.\d+|fastapi)\s+(updates|release|docs|version|features)\b",
        ]

    def detect_web_needed(self, query: str) -> bool:
        """
        Determines whether a user query requires live web search.
        
        Examples:
        - "What is recursion?" -> False
        - "What is the latest Python version?" -> True
        - "Find official FastAPI authentication docs" -> True
        """
        if not query or not query.strip():
            return False

        query_clean = query.strip().lower()

        # 1. Check if query matches a known static / conceptual pattern
        for pattern in self._static_patterns:
            if re.search(pattern, query_clean):
                # Double-check if explicit temporal words like 'latest' or 'today' override static pattern
                if not any(k in query_clean for k in ["latest", "today", "current", "2026", "2025"]):
                    return False

        # 2. Check explicit web triggers
        for trigger in self._web_triggers:
            if re.search(trigger, query_clean):
                return True

        # 3. Check web keywords
        tokens = set(re.findall(r"\b\w+\b", query_clean))
        if any(keyword in tokens for keyword in self._web_keywords):
            return True

        # 4. Specific domain/technology release queries
        if re.search(r"\b(api|sdk|framework|library|repo|github)\b", query_clean) and any(
            t in query_clean for t in ["how to", "find", "search", "show", "get", "where"]
        ):
            return True

        return False

    def classify_intent(self, query: str) -> WebSearchIntent:
        """
        Deterministically classifies query intent into one of 10 supported WebSearchIntent categories.
        """
        if not query or not query.strip():
            return WebSearchIntent.GENERAL

        q = query.strip().lower()

        # FACT_CHECK
        if any(k in q for k in ["is it true", "fact check", "did really", "verified", "hoax"]):
            return WebSearchIntent.FACT_CHECK

        # DOCUMENTATION
        if any(k in q for k in ["docs", "documentation", "api ref", "guide", "tutorial", "manual", "sdk docs"]):
            return WebSearchIntent.DOCUMENTATION

        # OFFICIAL_SOURCE
        if any(k in q for k in ["official site", "official website", "official repo", "download page", "homepage"]):
            return WebSearchIntent.OFFICIAL_SOURCE

        # ACADEMIC
        if any(k in q for k in ["paper", "arxiv", "study", "research", "journal", "citation", "conference"]):
            return WebSearchIntent.ACADEMIC

        # COMPARISON
        if any(k in q for k in [" vs ", " versus ", "compare", "difference between", "better than"]):
            return WebSearchIntent.COMPARISON

        # TECHNICAL
        if any(k in q for k in ["error", "traceback", "bug", "issue", "stack trace", "how to fix", "github issue"]):
            return WebSearchIntent.TECHNICAL

        # NAVIGATIONAL
        if any(k in q for k in ["login", "portal", "website", "url for", "link to", "download"]):
            return WebSearchIntent.NAVIGATIONAL

        # NEWS
        if any(k in q for k in ["news", "today", "breaking", "headline", "announcement", "what happened"]):
            return WebSearchIntent.NEWS

        # CURRENT_INFORMATION
        if any(k in q for k in ["latest", "current", "recent", "new", "release", "version", "update", "changelog"]):
            return WebSearchIntent.CURRENT_INFORMATION

        return WebSearchIntent.GENERAL


# Global singleton instance
intent_classifier = WebIntentClassifier()
