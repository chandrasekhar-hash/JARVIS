import re
from typing import Dict, Any, Optional, List, Set

# ---------------------------------------------------------------------------
# Centralized registries for known targets (websites and applications).
# Easy to extend without changing classifier logic.
# ---------------------------------------------------------------------------
KNOWN_WEBSITES: Dict[str, str] = {
    "youtube": "https://youtube.com",
    "yt": "https://youtube.com",
    "you tube": "https://youtube.com",
    "gmail": "https://mail.google.com",
    "google": "https://google.com",
    "github": "https://github.com",
    "chatgpt": "https://chat.openai.com",
    "claude": "https://claude.ai",
    "gemini": "https://gemini.google.com",
    "instagram": "https://instagram.com",
    "facebook": "https://facebook.com",
    "linkedin": "https://linkedin.com",
    "reddit": "https://reddit.com",
    "spotify": "https://spotify.com",
    "netflix": "https://netflix.com",
    "amazon": "https://amazon.in",
    "flipkart": "https://flipkart.com",
    "x": "https://x.com",
    "twitter": "https://x.com",
    "whatsapp": "https://web.whatsapp.com"
}

# The KNOWN_APPS static list has been removed. 
# Installed applications are resolved dynamically via the OS AppCacheManager.


def _normalize(text: str) -> str:
    """Lowercase, strip, collapse whitespace, remove trailing punctuation."""
    return re.sub(r"\s+", " ", text.lower().strip().rstrip(".!?"))


# Pre-compiled reasoning-keyword pattern (word-boundary anchored to prevent
# substring false-positives such as "what" matching inside "whatsapp").
_REASONING_PATTERN: re.Pattern = re.compile(
    r"\b(?:because|why|what|explain|summarize|compare|"
    r"search\s+for|find\s+out|analyze|describe)\b"
)


def classify_intent(query: str) -> Optional[Dict[str, Any]]:
    """
    Classifies a user query to a deterministic tool call.

    Priority order:
        1. Normalize the query.
        2. Check KNOWN_WEBSITES first.
        3. Then check dynamic application resolver.
        4. Only if neither matches, fall back to regex/LLM.

    Returns:
        Dict with ``tool_name`` and ``arguments`` on a confident match,
        or ``None`` for ambiguous / complex queries.
    """
    # 1. Normalize the query
    query_clean = _normalize(query)

    open_match = re.match(r"^open\s+(.+)$", query_clean)
    if open_match:
        target = open_match.group(1).strip()
        
        # 2. Check KNOWN_WEBSITES first
        if target in KNOWN_WEBSITES:
            return {
                "tool_name": "browser_open_url",
                "arguments": {"urls": [KNOWN_WEBSITES[target]]},
            }
            
        # 3. Check if target looks like a URL/domain name
        # e.g. starts with http://, https://, or www., or contains a dot followed by a 2-6 char domain suffix
        if target.startswith(("http://", "https://", "www.")) or re.search(r"\b[a-zA-Z0-9-]+\.[a-z]{2,6}(?:\b|/)", target):
            return {
                "tool_name": "browser_open_url",
                "arguments": {"urls": [target]},
            }
            
        # 4. Check dynamic resolver for application match
        from tools.app_discovery import AppCacheManager
        from tools.app_resolver import resolve_application, MATCH_SINGLE, MATCH_MULTIPLE
        cache_manager = AppCacheManager()
        app_list = cache_manager.load_or_refresh()
        status, matches = resolve_application(target, app_list)
        if status in (MATCH_SINGLE, MATCH_MULTIPLE):
            resolved_name = matches[0].name if status == MATCH_SINGLE else target
            return {
                "tool_name": "app_open",
                "arguments": {"name": resolved_name},
            }

    # 4. Only if neither matches, fall back to regex/LLM.
    # Reject long free-form queries (likely need LLM reasoning)
    if len(query_clean) > 55:
        return None

    # Reject reasoning / question words (word-boundary match to prevent
    # false positives like "what" inside "whatsapp" or "analyze" inside
    # an app name).
    if _REASONING_PATTERN.search(query_clean):
        return None

    # Reject queries with conflicting intents
    has_open  = "open"  in query_clean
    has_close = any(kw in query_clean for kw in ("close", "quit", "kill"))
    if has_open and has_close:
        return None

    # ── 2. Browser control shortcuts ─────────────────────────────────────────
    BROWSER_CONTROLS = {
        "scroll_down": [
            "scroll down", "scrollpage down", "scroll browser down",
        ],
        "scroll_up": [
            "scroll up", "scrollpage up", "scroll browser up",
        ],
        "scroll_top": [
            "scroll to top", "scroll top", "go to top",
        ],
        "scroll_bottom": [
            "scroll to bottom", "scroll bottom", "go to bottom",
        ],
        "close_tab": [
            "close current tab", "close tab", "close browser tab",
        ],
        "refresh": [
            "refresh", "refresh page", "reload", "reload page",
        ],
        "back": [
            "go back", "back in browser", "browser back",
        ],
        "forward": [
            "go forward", "forward in browser", "browser forward",
        ],
    }
    for action, phrases in BROWSER_CONTROLS.items():
        if query_clean in phrases:
            return {
                "tool_name": "browser_control",
                "arguments": {"action": action},
            }

    # ── 3. Filesystem shortcuts ───────────────────────────────────────────────
    FS_FOLDERS = {
        "Desktop":   ["open desktop", "go to desktop"],
        "Documents": ["open documents", "go to documents"],
        "Downloads": ["open downloads", "go to downloads"],
    }
    for folder, phrases in FS_FOLDERS.items():
        if query_clean in phrases:
            return {
                "tool_name": "fs_open_folder",
                "arguments": {"path": folder},
            }

    # Desktop item counts
    COUNT_ITEMS = {
        "folders": [
            "count desktop folders", "how many folders are on my desktop",
            "how many folders on my desktop", "count folders on desktop",
        ],
        "files": [
            "count desktop files", "how many files are on my desktop",
            "how many files on my desktop", "count files on desktop",
        ],
        "all": [
            "count desktop items", "count desktop files and folders",
            "how many items are on my desktop",
            "how many files and folders are on my desktop",
        ],
    }
    for item_type, phrases in COUNT_ITEMS.items():
        if query_clean in phrases:
            return {
                "tool_name": "fs_count_desktop_items",
                "arguments": {"item_type": item_type},
            }

    # ── 4. Desktop application open / close / switch (allowlist-gated) ───────
    if open_match:
        # Since dynamic application resolution has already been checked at the beginning of the function
        # and did not match, any remaining 'open <target>' is an unknown target.
        # Unknown target → let the LLM decide.
        return None

    close_match = re.match(r"^close\s+([a-zA-Z0-9\s_\-\.]+)$", query_clean)
    if close_match:
        app_name = close_match.group(1).strip()
        return {
            "tool_name": "app_close",
            "arguments": {"name": app_name},
        }

    switch_match1 = re.match(r"^switch\s+to\s+([a-zA-Z0-9\s_\-\.]+)$", query_clean)
    switch_match2 = re.match(
        r"^bring\s+([a-zA-Z0-9\s_\-\.]+)\s+to\s+(?:the\s+)?front$", query_clean
    )
    if switch_match1:
        return {
            "tool_name": "app_switch",
            "arguments": {"name": switch_match1.group(1).strip()},
        }
    if switch_match2:
        return {
            "tool_name": "app_switch",
            "arguments": {"name": switch_match2.group(1).strip()},
        }

    # 5. Refresh application index command
    refresh_phrases = {
        "refresh applications", "refresh installed applications", "refresh app index",
        "refresh apps", "update applications list", "update app list", "reload apps"
    }
    if query_clean in refresh_phrases:
        return {
            "tool_name": "app_refresh_index",
            "arguments": {}
        }

    return None
