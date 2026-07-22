import re
from typing import Optional
from brain.context import desktop_context
from tools.telemetry import log_structured, backend_log

class ReferenceResolver:
    def __init__(self):
        self.last_app: Optional[str] = None
        self.last_url: Optional[str] = None
        self.last_file: Optional[str] = None
        self.last_search: Optional[str] = None

    def register_mention(self, category: str, value: str) -> None:
        """Registers a mentioned entity into conversation memory."""
        if not value:
            return
        if category == "app":
            self.last_app = str(value)
            desktop_context.active_app = str(value)
        elif category == "url":
            self.last_url = str(value)
            desktop_context.active_tab = str(value)
        elif category == "file":
            self.last_file = str(value)
        elif category == "search":
            self.last_search = str(value)

        log_structured(backend_log, "INFO", f"[ReferenceResolver] Registered {category}: '{value}'")

    def resolve_references(self, query: str) -> str:
        """Resolves ambiguous pronouns in user query using conversation state."""
        query_strip = query.strip()
        query_lower = query_strip.lower()

        # 1. "close it" / "switch to it" -> refers to last app or active app
        target_app = self.last_app or desktop_context.active_app
        if target_app:
            if re.search(r'\b(close|switch to|maximize|minimize)\s+(it|this|that|the app)\b', query_lower):
                resolved = re.sub(r'\b(it|this|that|the app)\b', target_app, query_strip, flags=re.IGNORECASE)
                log_structured(backend_log, "INFO", f"[ReferenceResolver] Resolved query '{query_strip}' -> '{resolved}'")
                return resolved

        # 2. "summarize it" / "read it" -> refers to last URL or active tab
        target_url = self.last_url or desktop_context.active_tab
        if target_url:
            if re.search(r'\b(summarize|read|explain|open)\s+(it|this|that|the page|the url)\b', query_lower):
                resolved = re.sub(r'\b(it|this|that|the page|the url)\b', target_url, query_strip, flags=re.IGNORECASE)
                log_structured(backend_log, "INFO", f"[ReferenceResolver] Resolved query '{query_strip}' -> '{resolved}'")
                return resolved

        return query_strip

reference_resolver = ReferenceResolver()
