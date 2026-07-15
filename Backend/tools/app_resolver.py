import difflib
import re
from typing import List, Tuple, Dict
from tools.app_discovery import AppEntry

MATCH_SINGLE = "single"
MATCH_MULTIPLE = "multiple"
MATCH_NONE = "none"

# ---------------------------------------------------------------------------
# Well-known aliases that map informal names to common exe stems or display
# names. This is NOT a registry of apps — it simply bridges informal speech
# to the name the OS actually uses, e.g. "calculator" → "calc".
# ---------------------------------------------------------------------------
_ALIASES: Dict[str, str] = {
    "calculator": "calc",
    "calc": "calc",
    "vscode": "visual studio code",
    "vs code": "visual studio code",
    "code": "visual studio code",
    "chrome": "google chrome",
    "google chrome": "google chrome",
    "edge": "microsoft edge",
    "ms edge": "microsoft edge",
    "word": "microsoft word",
    "excel": "microsoft excel",
    "powerpoint": "microsoft powerpoint",
    "notepad": "notepad",
    "paint": "paint",
    "terminal": "windows terminal",
    "wt": "windows terminal",
    "winterm": "windows terminal",
}

# High-quality sources: display names are human-readable and meaningful.
_HIGH_QUALITY_SOURCES = {"start_menu", "registry"}


def clean_for_matching(s: str) -> str:
    """Lowercase, keep only alphanumeric characters."""
    return "".join(c for c in s.lower() if c.isalnum())


def _word_boundary_contains(haystack: str, needle: str) -> bool:
    """
    True if *needle* appears as a whole word (or phrase) inside *haystack*.
    Uses regex word boundaries so 'note' does NOT match inside 'notepad'.
    """
    if not needle:
        return False
    # Escape needle for regex, replace spaces with flexible whitespace
    pattern = r"(?i)(?<![\w])" + re.escape(needle).replace(r"\ ", r"[\s\-_]+") + r"(?![\w])"
    return bool(re.search(pattern, haystack))


def _candidate_display_name(app: AppEntry) -> str:
    """Returns the best human-readable name for matching purposes."""
    if app.source in _HIGH_QUALITY_SOURCES:
        return app.name  # Already a curated display name
    # For program_files / path entries the 'name' is just the exe stem;
    # use it as-is but callers know the quality is lower.
    return app.name


def deduplicate_by_target(apps: List[AppEntry]) -> List[AppEntry]:
    """Deduplicate entries by their normalized target executable path."""
    seen: set = set()
    out: List[AppEntry] = []
    for app in apps:
        key = app.target_path.lower().replace("/", "\\").rstrip("\\")
        if key not in seen:
            seen.add(key)
            out.append(app)
    return out


def _rank(app: AppEntry) -> int:
    """Lower is better. Used to surface high-quality sources first."""
    order = {"start_menu": 0, "registry": 1, "program_files": 2, "path": 3}
    return order.get(app.source, 9)


def resolve_application(query: str, app_list: List[AppEntry]) -> Tuple[str, List[AppEntry]]:
    """
    Resolve a free-text user query to one or more installed AppEntry objects.

    Resolution pipeline
    -------------------
    0. Alias expansion          — map informal names to canonical OS names
    1. Exact display-name match — case-insensitive, full string equality
    2. Exact exe-stem match     — e.g. "chrome" ↔ "chrome.exe"
    3. Word-boundary substring  — query is a *whole word* inside display name
    4. Prefix match             — display name starts with query
    5. Fuzzy match              — difflib on HIGH-QUALITY sources only

    Only MATCH_SINGLE is returned when we are confident.  
    MATCH_MULTIPLE is returned when 2+ distinct paths match the same step.
    MATCH_NONE if nothing passes.
    """
    query_raw = query.strip()
    if not query_raw:
        return MATCH_NONE, []

    query_lower = query_raw.lower()
    query_alpha = clean_for_matching(query_lower)

    # ── 0. Alias expansion ────────────────────────────────────────────────────
    canonical = _ALIASES.get(query_lower, query_lower)
    canonical_alpha = clean_for_matching(canonical)
    # Build a set of queries to try (original + alias-expanded)
    queries_to_try = [query_lower]
    if canonical != query_lower:
        queries_to_try.insert(0, canonical)  # alias takes priority

    # ── 1. Exact display-name match ───────────────────────────────────────────
    for q in queries_to_try:
        exact = [a for a in app_list if a.name.lower() == q]
        exact = deduplicate_by_target(exact)
        if len(exact) == 1:
            return MATCH_SINGLE, exact
        if len(exact) > 1:
            exact.sort(key=_rank)
            return MATCH_MULTIPLE, exact

    # ── 2. Exact exe-stem match ───────────────────────────────────────────────
    for q in queries_to_try:
        stem_hits = []
        for app in app_list:
            stem = app.target_path.replace("/", "\\").split("\\")[-1].lower()
            if stem == q or (stem.endswith(".exe") and stem[:-4] == q):
                stem_hits.append(app)
        stem_hits = deduplicate_by_target(stem_hits)
        # Prefer high-quality sources
        hq = [a for a in stem_hits if a.source in _HIGH_QUALITY_SOURCES]
        candidates = hq if hq else stem_hits
        if len(candidates) == 1:
            return MATCH_SINGLE, candidates
        if len(candidates) > 1:
            candidates.sort(key=_rank)
            return MATCH_MULTIPLE, candidates

    # ── 3. Word-boundary substring match (display name only) ─────────────────
    # Only search HIGH-QUALITY sources to avoid exe noise.
    for q in queries_to_try:
        wb_hits = [
            a for a in app_list
            if a.source in _HIGH_QUALITY_SOURCES
            and _word_boundary_contains(a.name, q)
        ]
        wb_hits = deduplicate_by_target(wb_hits)
        if len(wb_hits) == 1:
            return MATCH_SINGLE, wb_hits
        if len(wb_hits) > 1:
            wb_hits.sort(key=_rank)
            return MATCH_MULTIPLE, wb_hits

    # ── 4. Prefix match (display name) ───────────────────────────────────────
    for q in queries_to_try:
        prefix_hits = [
            a for a in app_list
            if a.source in _HIGH_QUALITY_SOURCES
            and a.name.lower().startswith(q)
        ]
        prefix_hits = deduplicate_by_target(prefix_hits)
        if len(prefix_hits) == 1:
            return MATCH_SINGLE, prefix_hits
        if len(prefix_hits) > 1:
            prefix_hits.sort(key=_rank)
            return MATCH_MULTIPLE, prefix_hits

    # ── 5. Fuzzy match (HIGH-QUALITY sources only, strict cutoff) ────────────
    hq_apps = [a for a in app_list if a.source in _HIGH_QUALITY_SOURCES]
    hq_name_map: Dict[str, AppEntry] = {}
    for app in hq_apps:
        # prefer shorter / cleaner display names when deduplicating the map
        key = app.name.lower()
        if key not in hq_name_map or _rank(app) < _rank(hq_name_map[key]):
            hq_name_map[key] = app

    for q in queries_to_try:
        close = difflib.get_close_matches(q, list(hq_name_map.keys()), n=5, cutoff=0.72)
        if close:
            fuzzy_hits = deduplicate_by_target([hq_name_map[n] for n in close])
            if len(fuzzy_hits) == 1:
                return MATCH_SINGLE, fuzzy_hits
            if len(fuzzy_hits) > 1:
                return MATCH_MULTIPLE, fuzzy_hits

    return MATCH_NONE, []
