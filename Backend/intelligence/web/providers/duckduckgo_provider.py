"""
DuckDuckGo Search Provider for J.A.R.V.I.S. I2.2 V1 Web Search Foundation.

Role: Zero-Key Development / Default Provider.
Disclaimer: DuckDuckGo HTML parsing is a zero-key development provider for initial setup and testing.
It does NOT offer contractual SLAs, guaranteed unlimited throughput, fixed quotas, static 300-600ms latency, or guaranteed layout structures.
BaseSearchProvider is kept cleanly decoupled so a contractual production search provider (e.g. Tavily, Brave, Serper) can replace it seamlessly.
"""
import re
import urllib.parse
import logging
from typing import List, Dict, Any, Optional
import httpx
from bs4 import BeautifulSoup

from intelligence.web.providers.base_provider import BaseSearchProvider
from tools.telemetry import log_structured, backend_log

logger = logging.getLogger("JARVIS_DuckDuckGoProvider")


class DuckDuckGoSearchProvider(BaseSearchProvider):
    """
    Zero-key development search provider leveraging DuckDuckGo HTML interface.
    Implements robust parsing, redirect URL resolution, and graceful failure handling.
    """

    def __init__(self, timeout_seconds: float = 10.0):
        self.timeout_seconds = timeout_seconds
        self.endpoint = "https://html.duckduckgo.com/html/"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

    def get_provider_name(self) -> str:
        return "DuckDuckGo"

    def _extract_real_url(self, raw_url: str) -> str:
        """
        Extracts real target URL from DuckDuckGo redirect wrapper (e.g. //duckduckgo.com/l/?uddg=http...).
        Returns cleaned absolute target URL.
        """
        if not raw_url:
            return ""

        url_str = raw_url.strip()
        if url_str.startswith("//"):
            url_str = "https:" + url_str

        parsed = urllib.parse.urlparse(url_str)
        if "duckduckgo.com" in parsed.netloc and "/l/" in parsed.path:
            qs = urllib.parse.parse_qs(parsed.query)
            if "uddg" in qs and qs["uddg"]:
                return qs["uddg"][0]

        # If it's a relative URL or direct target
        if url_str.startswith("http://") or url_str.startswith("https://"):
            return url_str
        
        # Unquote if percent-encoded
        return urllib.parse.unquote(url_str)

    async def search(self, query: str, max_results: int = 10, **kwargs) -> List[Dict[str, Any]]:
        """
        Executes DuckDuckGo search via HTTP POST and parses HTML results.
        Returns raw search dicts with title, url, snippet, provider_rank, raw_metadata.
        Never throws unhandled exceptions that crash the pipeline.
        """
        if not query or not query.strip():
            return []

        data = {"q": query.strip()}
        raw_results: List[Dict[str, Any]] = []

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
                response = await client.post(self.endpoint, data=data, headers=self.headers)
                if response.status_code != 200:
                    # Fallback to GET query on HTML or Lite endpoint
                    get_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
                    response = await client.get(get_url, headers=self.headers)

            if response.status_code != 200:
                log_structured(
                    backend_log,
                    "WARNING",
                    f"[DuckDuckGoProvider] Search failed with HTTP status {response.status_code} for query '{query}'",
                )
                return []

            html_content = response.text
            if not html_content or len(html_content.strip()) == 0:
                log_structured(
                    backend_log,
                    "WARNING",
                    f"[DuckDuckGoProvider] Empty HTML response received for query '{query}'",
                )
                return []

            soup = BeautifulSoup(html_content, "html.parser")

            # Parse DuckDuckGo HTML results
            result_nodes = soup.select(".result") or soup.find_all("div", class_="result__body")

            rank = 1
            for node in result_nodes:
                if rank > max_results * 2:  # Fetch excess to allow for deduplication/filtering
                    break

                # Extract Title & Link
                title_elem = node.select_one(".result__title") or node.select_one(".result__a") or node.find("a")
                url_elem = node.select_one(".result__url") or node.select_one(".result__snippet")

                if not title_elem:
                    continue

                raw_title = title_elem.get_text(strip=True)
                raw_href = title_elem.get("href", "") or (url_elem.get("href", "") if url_elem else "")

                if not raw_title or not raw_href:
                    continue

                target_url = self._extract_real_url(str(raw_href))
                if not target_url or not target_url.startswith("http"):
                    continue

                # Extract Snippet Summary
                snippet_elem = (
                    node.select_one(".result__snippet")
                    or node.select_one(".result-snippet")
                    or node.find("td", class_="result-snippet")
                )
                raw_snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                # Extract optional date strings if embedded in snippet
                published_at_raw = None
                date_match = re.search(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}\b", raw_snippet)
                if date_match:
                    published_at_raw = date_match.group(0)

                raw_results.append({
                    "title": raw_title,
                    "url": target_url,
                    "snippet": raw_snippet,
                    "provider": self.get_provider_name(),
                    "provider_rank": rank,
                    "published_at_raw": published_at_raw,
                    "query_used": query,
                })
                rank += 1

            return raw_results

        except httpx.TimeoutException:
            log_structured(
                backend_log,
                "WARNING",
                f"[DuckDuckGoProvider] Timeout ({self.timeout_seconds}s) performing search for query '{query}'",
            )
            return []
        except httpx.HTTPStatusError as http_err:
            log_structured(
                backend_log,
                "WARNING",
                f"[DuckDuckGoProvider] HTTP error {http_err.response.status_code} for query '{query}'",
            )
            return []
        except Exception as exc:
            log_structured(
                backend_log,
                "WARNING",
                f"[DuckDuckGoProvider] Exception parsing search results for query '{query}': {str(exc)}",
            )
            return []
