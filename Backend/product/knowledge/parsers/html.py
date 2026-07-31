"""
JARVIS Product 1.6 - HTML Parser.
Parses HTML document structure using BeautifulSoup4 or regex.
"""

import os
import re
import logging
from typing import Tuple, Dict, Any, Optional
from .base import BaseParser

logger = logging.getLogger(__name__)


class HTMLParser(BaseParser):
    def __init__(self):
        super().__init__("HTMLParser")

    def can_parse(self, source: str, mime_type: Optional[str] = None) -> bool:
        if mime_type and mime_type.lower() == "text/html":
            return True
        ext = os.path.splitext(source)[1].lower()
        return ext in (".html", ".htm", ".xhtml")

    def parse(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"HTML file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            raw_html = f.read()

        title = "HTML Document"
        extracted_text = ""

        try:
            from bs4 import BeautifulSoup  # type: ignore
            soup = BeautifulSoup(raw_html, "html.parser")
            if soup.title and soup.title.string:
                title = soup.title.string.strip()
            
            # Remove scripts & styles
            for elem in soup(["script", "style", "nav", "footer"]):
                elem.decompose()

            extracted_text = soup.get_text(separator="\n\n").strip()
            metadata = {"title": title, "parsed_with": "BeautifulSoup4"}
            return extracted_text, metadata
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"BeautifulSoup HTML parsing failed for {file_path}: {e}")

        # Regex fallback
        clean_text = re.sub(r"<style.*?>.*?</style>", "", raw_html, flags=re.DOTALL)
        clean_text = re.sub(r"<script.*?>.*?</script>", "", clean_text, flags=re.DOTALL)
        clean_text = re.sub(r"<[^>]+>", " ", clean_text)
        clean_text = re.sub(r"\s+", " ", clean_text).strip()

        title_match = re.search(r"<title>(.*?)</title>", raw_html, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()

        return clean_text, {"title": title, "parsed_with": "regex_fallback"}
