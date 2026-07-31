"""
JARVIS Product 1.6 - Source Code Parser.
Parses code files (Python, JS, TS, C++, Rust, Go, Java, etc.) retaining structure and symbols.
"""

import os
import logging
from typing import Tuple, Dict, Any, Optional
from .base import BaseParser

logger = logging.getLogger(__name__)

CODE_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".sh": "bash",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".sql": "sql",
}


class CodeParser(BaseParser):
    def __init__(self):
        super().__init__("CodeParser")

    def can_parse(self, source: str, mime_type: Optional[str] = None) -> bool:
        ext = os.path.splitext(source)[1].lower()
        return ext in CODE_EXTENSIONS

    def parse(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Code file not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        language = CODE_EXTENSIONS.get(ext, "code")

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code_text = f.read()

        lines = code_text.splitlines()
        symbols = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("def ") or stripped.startswith("class ") or stripped.startswith("function ") or stripped.startswith("pub fn "):
                symbols.append(stripped.split("(")[0])

        formatted_code = f"``` {language}\n// File: {os.path.basename(file_path)}\n{code_text}\n```"

        metadata = {
            "language": language,
            "line_count": len(lines),
            "symbols_detected": symbols[:30],
        }

        return formatted_code, metadata
