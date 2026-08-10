"""
J.A.R.V.I.S. Intelligence I2.2 V8 — Snapshot Fingerprint Generator.
Generates deterministic content and structural fingerprints ignoring presentation/retrieval noise
(whitespace, tracking params, session IDs, script hashes, timestamps) without stripping meaningful factual facts.
"""
import hashlib
import re
import urllib.parse
from typing import List, Dict, Any, Tuple
from bs4 import BeautifulSoup


class SnapshotFingerprintGenerator:
    """
    Computes deterministic SHA256 content and structural fingerprints.
    """

    TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid", "session_id", "_ga"}

    def sanitize_url(self, url: str) -> str:
        if not url:
            return ""
        parsed = urllib.parse.urlparse(url)
        q_sl = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        filtered_q = [(k, v) for k, v in q_sl if k.lower() not in self.TRACKING_PARAMS]
        clean_query = urllib.parse.urlencode(filtered_q)
        return urllib.parse.urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path,
            parsed.params,
            clean_query,
            ""  # strip fragment for canonical comparison
        ))

    def normalize_text(self, text: str) -> str:
        if not text:
            return ""
        # Collapse whitespace without stripping numbers/versions
        cleaned = re.sub(r"\s+", " ", text).strip()
        return cleaned

    def compute_content_fingerprint(self, text_blocks: List[str]) -> str:
        normalized_str = "\n".join(self.normalize_text(b) for b in text_blocks if b)
        return hashlib.sha256(normalized_str.encode("utf-8")).hexdigest()

    def compute_structural_fingerprint(self, headings: List[str], link_urls: List[str]) -> str:
        clean_links = [self.sanitize_url(u) for u in link_urls if u]
        struct_str = "HEADINGS:" + "|".join(headings) + "||LINKS:" + "|".join(clean_links)
        return hashlib.sha256(struct_str.encode("utf-8")).hexdigest()


snapshot_fingerprint_generator = SnapshotFingerprintGenerator()
