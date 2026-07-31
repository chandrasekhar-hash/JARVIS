"""
JARVIS Product 1.6 - TXT / Markdown Parser.
"""

import os
import logging
from typing import Tuple, Dict, Any, Optional
from .base import BaseParser

logger = logging.getLogger(__name__)


class TxtMarkdownParser(BaseParser):
    def __init__(self):
        super().__init__("TxtMarkdownParser")

    def can_parse(self, source: str, mime_type: Optional[str] = None) -> bool:
        if mime_type and mime_type.lower() in ("text/plain", "text/markdown"):
            return True
        ext = os.path.splitext(source)[1].lower()
        return ext in (".txt", ".md", ".markdown", ".rst", ".log", ".note")

    def parse(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Text file not found: {file_path}")

        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
        content = ""
        used_encoding = "utf-8"

        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    content = f.read()
                used_encoding = enc
                break
            except (UnicodeDecodeError, Exception):
                continue

        lines = content.splitlines()
        headers = [line.strip() for line in lines if line.strip().startswith("#")]

        metadata = {
            "char_count": len(content),
            "line_count": len(lines),
            "encoding": used_encoding,
            "markdown_headers": headers[:20],
        }

        return content, metadata
