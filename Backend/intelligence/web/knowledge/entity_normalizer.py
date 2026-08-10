"""
Deterministic Entity Normalization for J.A.R.V.I.S. I2.2 V9.
"""
import re
import unicodedata
from typing import Optional


class EntityNormalizer:
    """
    Normalizes surface text into deterministic normalized keys without destroying
    original surface text or source evidence.
    """

    ORG_SUFFIX_RE = re.compile(
        r"\b(inc|inc\.|corp|corp\.|corporation|llc|ltd|ltd\.|limited|co\.|company)\b",
        re.IGNORECASE,
    )
    VERSION_PREFIX_RE = re.compile(r"^v(?:ersion)?\s*(\d+.*)$", re.IGNORECASE)
    JS_SUFFIX_RE = re.compile(r"(\b\w+)(?:\.js|js)\b", re.IGNORECASE)

    def normalize(self, surface_text: str) -> str:
        if not surface_text:
            return ""

        # 1. Unicode NFC normalization
        normalized = unicodedata.normalize("NFC", surface_text)

        # 2. Whitespace collapse
        normalized = " ".join(normalized.strip().split())

        # 3. Lowercase
        normalized_lower = normalized.lower()

        # 4. Handle version strings (e.g. "v3.14" -> "3.14", "Version 3.14" -> "3.14")
        ver_match = self.VERSION_PREFIX_RE.match(normalized_lower)
        if ver_match:
            return ver_match.group(1).strip()

        # 5. Handle JS framework variants (e.g. "react.js", "reactjs" -> "react")
        if normalized_lower in ("react.js", "reactjs", "react"):
            return "react"
        if normalized_lower in ("vue.js", "vuejs", "vue"):
            return "vue"
        if normalized_lower in ("node.js", "nodejs", "node"):
            return "node"
        if normalized_lower in ("next.js", "nextjs", "next"):
            return "next"

        # 6. Organization suffix strip for normalized comparison
        normalized_org = self.ORG_SUFFIX_RE.sub("", normalized_lower).strip()
        normalized_org = re.sub(r"\s+", " ", normalized_org).strip(",")

        if normalized_org and len(normalized_org) > 1:
            return normalized_org

        return normalized_lower

    def normalize_version(self, version_str: str) -> str:
        if not version_str:
            return ""
        v = version_str.strip().lower()
        v = re.sub(r"^v(?:ersion)?\s*", "", v)
        return v.strip()


entity_normalizer = EntityNormalizer()
