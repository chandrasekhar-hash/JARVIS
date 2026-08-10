"""
J.A.R.V.I.S. Intelligence I2.2 V8 — Monitoring Policy & Target Identity Validator.
Enforces static-first retrieval policy and validates target identity continuity across redirects/canonical URL transitions.
"""
import urllib.parse
import logging
from typing import Tuple, Optional

logger = logging.getLogger("JARVIS_MonitoringPolicy")


class MonitoringPolicy:
    """
    Evaluates target identity continuity and static-first escalation rules for monitoring operations.
    """

    def validate_target_identity_continuity(
        self, original_url: str, canonical_url: str
    ) -> Tuple[bool, str]:
        if not original_url or not canonical_url:
            return False, "Missing URL identity parameter"

        p1 = urllib.parse.urlparse(original_url)
        p2 = urllib.parse.urlparse(canonical_url)

        # Allow HTTP -> HTTPS scheme upgrade
        if p1.scheme != p2.scheme and not (p1.scheme == "http" and p2.scheme == "https"):
            return False, f"Disallowed scheme transition: {p1.scheme} -> {p2.scheme}"

        # Allow www prefix stripping / addition on same domain
        host1 = p1.netloc.lower().replace("www.", "")
        host2 = p2.netloc.lower().replace("www.", "")

        if host1 != host2:
            logger.warning(f"Domain migration detected: {host1} -> {host2}. Identity continuity lost.")
            return False, f"Domain migration lost identity continuity: {host1} -> {host2}"

        return True, "Target identity continuity validated."


monitoring_policy = MonitoringPolicy()
