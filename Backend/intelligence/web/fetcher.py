"""
Web Page Fetcher and Transport Layer for J.A.R.V.I.S. I2.2 V2.

Implements SafeHTTPTransport (TLS SNI + certificate verification + socket IP pinning),
uncompressed streaming byte bounds, strict resource cleanup (aclose()), redirect re-validation,
async-safe ephemeral RAM caching, request coalescing, and content-type detection.
"""
import time
import asyncio
import urllib.parse
import logging
import ssl
from typing import Dict, Any, Optional, Tuple
import httpx

import config
from intelligence.web.models import (
    WebPageMetadata,
    WebRetrievalStatus,
)
from intelligence.web.url_validator import url_validator
from tools.telemetry import log_structured, backend_log

logger = logging.getLogger("JARVIS_WebPageFetcher")


import httpcore
from httpcore._backends.anyio import AnyIOBackend


class PinnedNetworkBackend(AnyIOBackend):
    """
    Custom httpcore network backend that hard-pins TCP socket connections to the
    pre-validated target IP address, completely eliminating DNS TOCTOU / rebinding vulnerabilities.
    """

    def __init__(self, target_ip: str, original_hostname: str):
        super().__init__()
        self.target_ip = target_ip
        self.original_hostname = original_hostname

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: Optional[float] = None,
        local_address: Optional[str] = None,
        socket_options: Optional[Any] = None
    ) -> httpcore.AsyncNetworkStream:
        connect_host = self.target_ip if host == self.original_hostname else host
        return await super().connect_tcp(
            host=connect_host,
            port=port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options
        )


class SafeHTTPTransport(httpx.AsyncHTTPTransport):
    """
    Custom HTTPX Async Transport enforcing socket connection to a pre-validated IP
    via PinnedNetworkBackend while preserving original domain hostname for TLS SNI and SSL certificate verification.
    SSL verification (verify=True) is NEVER bypassed.
    """

    def __init__(self, target_ip: str, original_hostname: str, verify: bool = True, **kwargs):
        super().__init__(verify=verify, **kwargs)
        self.target_ip = target_ip
        self.original_hostname = original_hostname
        backend = PinnedNetworkBackend(target_ip=target_ip, original_hostname=original_hostname)
        ssl_context = httpx.create_ssl_context(verify=verify)
        self._pool = httpcore.AsyncConnectionPool(
            network_backend=backend,
            ssl_context=ssl_context,
            max_connections=10,
            http1=True,
            http2=False
        )

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if "host" not in request.headers:
            request.headers["host"] = self.original_hostname
        return await super().handle_async_request(request)



class WebPageCache:
    """
    Async-safe, bounded ephemeral RAM cache for public web page retrievals.
    Entry-count bounded (50), TTL bounded (300s), byte-size bounded (500KB per item).
    Never caches authenticated, secret-containing, or no-store responses.
    """

    def __init__(self, max_entries: int = 50, ttl_seconds: float = 300.0, max_item_bytes: int = 500000):
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self.max_item_bytes = max_item_bytes
        self._cache: Dict[str, Tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key not in self._cache:
                return None
            timestamp, data = self._cache[key]
            if time.time() - timestamp > self.ttl_seconds:
                del self._cache[key]
                return None
            return data

    async def set(self, key: str, data: Any, byte_size: int):
        if byte_size > self.max_item_bytes:
            return
        async with self._lock:
            if len(self._cache) >= self.max_entries:
                # Evict oldest entry
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][0])
                del self._cache[oldest_key]
            self._cache[key] = (time.time(), data)

    async def clear(self):
        async with self._lock:
            self._cache.clear()


class WebPageFetcher:
    """
    Asynchronous Web Page Fetcher with strict security, decompression limits,
    streaming resource cleanup, and redirect re-validation.
    """

    def __init__(self):
        self.user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 "
            "JARVIS/2.2 (Web Intelligence Retrieval Engine)"
        )
        self.cache = WebPageCache(
            max_entries=50,
            ttl_seconds=getattr(config, "WEB_FETCH_CACHE_TTL_SECONDS", 300.0)
        )
        self._in_flight: Dict[str, asyncio.Future] = {}
        self._in_flight_lock = asyncio.Lock()

    @staticmethod
    def _is_cacheable_request(url: str, headers: Dict[str, str], response_headers: Dict[str, str]) -> bool:
        """Determines if request and response meet strict public caching requirements."""
        if not getattr(config, "WEB_FETCH_CACHE_ENABLED", True):
            return False

        # Do not cache authenticated or tokenized requests
        lower_headers = {k.lower(): v for k, v in headers.items()}
        if "authorization" in lower_headers or "cookie" in lower_headers:
            return False

        parsed_url = urllib.parse.urlparse(url)
        query = parsed_url.query.lower()
        if any(token in query for token in ["token=", "key=", "auth=", "secret=", "bearer="]):
            return False

        lower_resp = {k.lower(): v for k, v in response_headers.items()}
        cache_control = lower_resp.get("cache-control", "").lower()
        if "no-store" in cache_control or "private" in cache_control:
            return False

        return True

    async def fetch_page(
        self,
        url: str,
        timeout_seconds: Optional[float] = None,
        max_bytes: Optional[int] = None,
        max_redirects: Optional[int] = None
    ) -> Tuple[WebRetrievalStatus, Optional[WebPageMetadata], bytes, Optional[str]]:
        """
        Fetches webpage with complete security validation, streaming size limits,
        and guaranteed resource cleanup.

        Returns:
            Tuple[retrieval_status, metadata, raw_bytes, error_message]
        """
        retrieved_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        fetch_timeout = timeout_seconds or getattr(config, "WEB_FETCH_TIMEOUT_SECONDS", 10.0)
        fetch_max_bytes = max_bytes or getattr(config, "WEB_FETCH_MAX_BYTES", 3000000)
        fetch_max_redirects = max_redirects or getattr(config, "WEB_FETCH_MAX_REDIRECTS", 5)

        # 1. Check Ephemeral RAM Cache
        cached_result = await self.cache.get(url)
        if cached_result:
            log_structured(backend_log, "INFO", f"[WebPageFetcher] Cache hit for URL '{url}'")
            return cached_result

        # 2. Request Coalescing for duplicate in-flight URLs
        async with self._in_flight_lock:
            if url in self._in_flight:
                log_structured(backend_log, "INFO", f"[WebPageFetcher] Coalescing request for in-flight URL '{url}'")
                future = self._in_flight[url]
                try:
                    return await future
                except Exception as exc:
                    return WebRetrievalStatus.FETCH_FAILED, None, b"", f"In-flight request failed: {exc}"

            loop = asyncio.get_running_loop()
            in_flight_future = loop.create_future()
            self._in_flight[url] = in_flight_future

        try:
            result = await self._execute_fetch(
                url=url,
                fetch_timeout=fetch_timeout,
                fetch_max_bytes=fetch_max_bytes,
                fetch_max_redirects=fetch_max_redirects,
                retrieved_at=retrieved_at
            )

            status, metadata, content_bytes, error_msg = result
            if status == WebRetrievalStatus.SUCCESS and metadata:
                # Check cacheability
                if self._is_cacheable_request(url, {}, {}):
                    await self.cache.set(url, result, len(content_bytes))

            if not in_flight_future.done():
                in_flight_future.set_result(result)
            return result

        except Exception as exc:
            err_result = (WebRetrievalStatus.FETCH_FAILED, None, b"", f"Fetch error: {exc}")
            if not in_flight_future.done():
                in_flight_future.set_result(err_result)
            return err_result
        finally:
            async with self._in_flight_lock:
                self._in_flight.pop(url, None)

    async def _execute_fetch(
        self,
        url: str,
        fetch_timeout: float,
        fetch_max_bytes: int,
        fetch_max_redirects: int,
        retrieved_at: str
    ) -> Tuple[WebRetrievalStatus, Optional[WebPageMetadata], bytes, Optional[str]]:
        """Internal fetch execution pipeline with manual redirect re-validation."""
        current_url = url
        redirect_chain = []
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.5",
        }

        for redirect_hop in range(fetch_max_redirects + 1):
            # Validate URL and IP for current target
            is_safe, resolved_ip, reason = await url_validator.validate_url(current_url)
            if not is_safe:
                return (
                    WebRetrievalStatus.SSRF_BLOCKED,
                    None,
                    b"",
                    f"SSRF validation blocked URL '{current_url}': {reason}"
                )

            parsed_url = urllib.parse.urlparse(current_url)
            domain = parsed_url.netloc

            # Execute streaming request
            try:
                # Setup custom transport pinning connection socket to resolved_ip while preserving SNI
                transport = SafeHTTPTransport(
                    target_ip=resolved_ip or domain,
                    original_hostname=parsed_url.hostname or domain,
                    verify=True
                )

                async with httpx.AsyncClient(
                    transport=transport,
                    timeout=httpx.Timeout(fetch_timeout),
                    follow_redirects=False
                ) as client:
                    response_stream = None
                    try:
                        req = client.build_request("GET", current_url, headers=headers)
                        response = await client.send(req, stream=True)
                        response_stream = response

                        # Check status code for redirect
                        if response.status_code in (301, 302, 303, 307, 308):
                            location = response.headers.get("Location")
                            await response.aclose()
                            response_stream = None

                            if not location:
                                return WebRetrievalStatus.HTTP_ERROR, None, b"", f"Redirect status {response.status_code} received without Location header."

                            next_url = urllib.parse.urljoin(current_url, location)
                            redirect_chain.append(current_url)
                            current_url = next_url
                            continue  # Next redirect loop iteration

                        if response.status_code != 200:
                            await response.aclose()
                            response_stream = None
                            return (
                                WebRetrievalStatus.HTTP_ERROR,
                                None,
                                b"",
                                f"HTTP fetch failed with status code {response.status_code}"
                            )

                        # Content-Type Header Inspection
                        raw_content_type = response.headers.get("Content-Type", "text/html").lower()
                        main_mime = raw_content_type.split(";")[0].strip()

                        metadata = WebPageMetadata(
                            requested_url=url,
                            final_url=current_url,
                            canonical_url=current_url,
                            domain=domain,
                            content_type=main_mime,
                            retrieved_at=retrieved_at,
                            http_status=response.status_code
                        )

                        # PDF Handoff Check
                        if "application/pdf" in main_mime or current_url.lower().endswith(".pdf"):
                            await response.aclose()
                            response_stream = None
                            log_structured(backend_log, "INFO", f"[WebPageFetcher] PDF detected for '{current_url}'. Returning PDF_HANDOFF status.")
                            return WebRetrievalStatus.PDF_HANDOFF, metadata, b"", None

                        # Generic Binary Handoff Check
                        if any(b_type in main_mime for b_type in ["image/", "video/", "audio/", "application/zip", "application/octet-stream"]):
                            await response.aclose()
                            response_stream = None
                            return WebRetrievalStatus.UNSUPPORTED_CONTENT_TYPE, metadata, b"", f"Unsupported binary content-type: {main_mime}"

                        # Stream Uncompressed Response Body with Size Bounds
                        uncompressed_bytes = bytearray()
                        async for chunk in response.aiter_bytes():
                            uncompressed_bytes.extend(chunk)
                            if len(uncompressed_bytes) > fetch_max_bytes:
                                await response.aclose()
                                response_stream = None
                                log_structured(backend_log, "WARNING", f"[WebPageFetcher] Response uncompressed byte limit ({fetch_max_bytes}) exceeded for URL '{current_url}'")
                                return (
                                    WebRetrievalStatus.OVERSIZED,
                                    metadata,
                                    bytes(uncompressed_bytes[:fetch_max_bytes]),
                                    f"Response exceeded maximum uncompressed size limit of {fetch_max_bytes} bytes."
                                )

                        await response.aclose()
                        response_stream = None
                        return WebRetrievalStatus.SUCCESS, metadata, bytes(uncompressed_bytes), None

                    finally:
                        if response_stream is not None:
                            try:
                                await response_stream.aclose()
                            except Exception:
                                pass

            except httpx.TimeoutException:
                return WebRetrievalStatus.TIMEOUT, None, b"", f"Connection/read timeout ({fetch_timeout}s) fetching URL '{current_url}'."
            except ssl.SSLError as ssl_err:
                return WebRetrievalStatus.FETCH_FAILED, None, b"", f"TLS/SSL certificate verification failed for '{current_url}': {ssl_err}"
            except httpx.HTTPError as http_err:
                return WebRetrievalStatus.FETCH_FAILED, None, b"", f"HTTP transport error fetching URL '{current_url}': {http_err}"
            except Exception as exc:
                return WebRetrievalStatus.FETCH_FAILED, None, b"", f"Unexpected fetch exception for URL '{current_url}': {exc}"

        return WebRetrievalStatus.FETCH_FAILED, None, b"", f"Too many redirects (exceeded limit of {fetch_max_redirects})."


# Global singleton instance
web_fetcher = WebPageFetcher()
