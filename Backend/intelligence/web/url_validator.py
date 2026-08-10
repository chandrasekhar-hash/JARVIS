"""
URL Safety and SSRF Prevention Validator for J.A.R.V.I.S. I2.2 V2.

Validates requested URLs, normalizes IP representations (decimal, octal, hex, integer),
enforces Python ipaddress safety checks, performs DNS resolution, and protects against
SSRF, private network leakage, and DNS rebinding attacks.
"""
import re
import socket
import asyncio
import urllib.parse
import ipaddress
import logging
from typing import Tuple, Optional, List

from tools.telemetry import log_structured, backend_log

logger = logging.getLogger("JARVIS_UrlSafetyValidator")


class UrlSafetyValidator:
    """
    Dedicated SSRF Prevention and URL Safety Validator.
    Enforces strict scheme checks, IP address range checks, and DNS resolution validation.
    """

    ALLOWED_SCHEMES = {"http", "https"}
    BLOCKED_HOSTNAMES = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}

    @staticmethod
    def _parse_encoded_ip(hostname: str) -> Optional[ipaddress.IPv4Address | ipaddress.IPv6Address]:
        """
        Attempts to parse unusual IP encodings (integer, hex, octal, standard dotted/colon).
        Returns normalized ipaddress object or None if hostname is a domain name.
        """
        clean_host = hostname.strip()

        # Remove IPv6 brackets if present
        if clean_host.startswith("[") and clean_host.endswith("]"):
            clean_host = clean_host[1:-1]

        # 1. Standard ipaddress parse attempt
        try:
            return ipaddress.ip_address(clean_host)
        except ValueError:
            pass

        # 2. Integer-encoded IPv4 (e.g. 2130706433 -> 127.0.0.1)
        if clean_host.isdigit():
            try:
                ip_int = int(clean_host)
                if 0 <= ip_int <= 4294967295:
                    return ipaddress.IPv4Address(ip_int)
            except ValueError:
                pass

        # 3. Hex-encoded IPv4 (e.g. 0x7f000001 or 0x7f.0x0.0x0.0x1)
        if clean_host.lower().startswith("0x"):
            try:
                ip_int = int(clean_host, 16)
                if 0 <= ip_int <= 4294967295:
                    return ipaddress.IPv4Address(ip_int)
            except ValueError:
                pass

        # 4. Octal or mixed-hex dotted IPv4 notation (e.g. 0177.0.0.1 or 0x7f.0.0.1)
        parts = clean_host.split(".")
        if len(parts) == 4:
            try:
                parsed_octets = []
                for p in parts:
                    if p.lower().startswith("0x"):
                        parsed_octets.append(int(p, 16))
                    elif p.startswith("0") and len(p) > 1 and p.isdigit():
                        parsed_octets.append(int(p, 8))
                    elif p.isdigit():
                        parsed_octets.append(int(p, 10))
                    else:
                        return None
                if all(0 <= o <= 255 for o in parsed_octets):
                    return ipaddress.IPv4Address(bytes(parsed_octets))
            except ValueError:
                pass

        return None

    @classmethod
    def is_ip_unsafe(cls, ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address) -> Tuple[bool, str]:
        """
        Evaluates whether an IP address object belongs to private, loopback, link-local,
        unspecified, multicast, reserved, or non-global ranges.
        """
        # Handle IPv4-mapped IPv6 address (e.g. ::ffff:10.0.0.1) and NAT64 IPv6 addresses (64:ff9b::/96)
        if isinstance(ip_obj, ipaddress.IPv6Address):
            if ip_obj.ipv4_mapped:
                ip_obj = ip_obj.ipv4_mapped
            else:
                # NAT64 Well-Known Prefix (64:ff9b::/96) and local prefix (64:ff9b:1::/48)
                nat64_wkp = ipaddress.IPv6Network("64:ff9b::/96")
                nat64_local = ipaddress.IPv6Network("64:ff9b:1::/48")
                if ip_obj in nat64_wkp or ip_obj in nat64_local:
                    ip_obj = ipaddress.IPv4Address(ip_obj.packed[-4:])

        if ip_obj.is_private:
            return True, f"Private IP address rejected: {ip_obj}"
        if ip_obj.is_loopback:
            return True, f"Loopback IP address rejected: {ip_obj}"
        if ip_obj.is_link_local:
            return True, f"Link-local IP address rejected: {ip_obj}"
        if ip_obj.is_unspecified:
            return True, f"Unspecified IP address rejected: {ip_obj}"
        if ip_obj.is_multicast:
            return True, f"Multicast IP address rejected: {ip_obj}"
        if ip_obj.is_reserved:
            return True, f"Reserved IP address rejected: {ip_obj}"
        if not ip_obj.is_global:
            return True, f"Non-global IP address rejected: {ip_obj}"

        return False, ""

    @classmethod
    async def validate_url(cls, url: str) -> Tuple[bool, Optional[str], str]:
        """
        Validates URL scheme, hostname, IP encodings, and performs DNS resolution.

        Returns:
            Tuple[is_safe (bool), resolved_ip (Optional[str]), reason/message (str)]
        """
        if not url or not url.strip():
            return False, None, "URL is empty."

        clean_url = url.strip()

        try:
            parsed = urllib.parse.urlparse(clean_url)
        except Exception as parse_err:
            return False, None, f"Malformed URL string: {parse_err}"

        # 1. Scheme Check
        if not parsed.scheme or parsed.scheme.lower() not in cls.ALLOWED_SCHEMES:
            return False, None, f"Disallowed URL scheme '{parsed.scheme}'. Only http and https allowed."

        # 2. Hostname Presence Check
        hostname = parsed.hostname
        if not hostname:
            return False, None, "URL has no valid hostname."

        hostname_lower = hostname.lower().strip()

        # 3. Direct String Blocklist Check
        if hostname_lower in cls.BLOCKED_HOSTNAMES:
            return False, None, f"Explicitly blocked hostname: {hostname}"

        # 4. Direct IP Encoding Parse Check
        ip_obj = cls._parse_encoded_ip(hostname_lower)
        if ip_obj:
            is_unsafe, reason = cls.is_ip_unsafe(ip_obj)
            if is_unsafe:
                log_structured(backend_log, "WARNING", f"[UrlSafetyValidator] {reason} for URL '{url}'")
                return False, None, reason
            return True, str(ip_obj), "Valid public IP destination."

        # 5. DNS Resolution Check for Domain Hostnames
        try:
            loop = asyncio.get_running_loop()
            # Resolve A / AAAA records
            addr_info = await loop.getaddrinfo(
                hostname_lower,
                parsed.port or (443 if parsed.scheme == "https" else 80),
                family=socket.AF_UNSPEC,
                type=socket.SOCK_STREAM
            )
        except socket.gaierror as dns_err:
            return False, None, f"DNS resolution failed for domain '{hostname}': {dns_err}"
        except Exception as exc:
            return False, None, f"Unexpected error during DNS resolution for domain '{hostname}': {exc}"

        if not addr_info:
            return False, None, f"No DNS records found for domain '{hostname}'."

        resolved_ips: List[str] = []
        for family, socktype, proto, canonname, sockaddr in addr_info:
            ip_str = sockaddr[0]
            try:
                resolved_ip_obj = ipaddress.ip_address(ip_str)
                is_unsafe, reason = cls.is_ip_unsafe(resolved_ip_obj)
                if is_unsafe:
                    log_structured(backend_log, "WARNING", f"[UrlSafetyValidator] Domain '{hostname}' resolved to unsafe IP: {reason}")
                    return False, None, f"Domain '{hostname}' resolved to internal IP ({ip_str}): {reason}"
                resolved_ips.append(str(resolved_ip_obj))
            except ValueError:
                return False, None, f"Invalid IP returned by DNS for domain '{hostname}': {ip_str}"

        primary_resolved_ip = resolved_ips[0] if resolved_ips else None
        return True, primary_resolved_ip, f"Domain '{hostname}' validated successfully (Resolved IP: {primary_resolved_ip})."


# Global singleton instance
url_validator = UrlSafetyValidator()
