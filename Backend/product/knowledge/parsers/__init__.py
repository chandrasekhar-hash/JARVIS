"""
JARVIS Product 1.6 - Parser Registry & Factory.
"""

import os
from typing import List, Optional
from .base import BaseParser
from .pdf import PDFParser
from .docx import DocxParser
from .txt_md import TxtMarkdownParser
from .html import HTMLParser
from .code import CodeParser
from .image_ocr import ImageOCRParser


class ParserFactory:
    def __init__(self):
        self.parsers: List[BaseParser] = [
            PDFParser(),
            DocxParser(),
            TxtMarkdownParser(),
            HTMLParser(),
            CodeParser(),
            ImageOCRParser(),
        ]

    def get_parser(self, source: str, mime_type: Optional[str] = None) -> BaseParser:
        for parser in self.parsers:
            if parser.can_parse(source, mime_type):
                return parser
        # Default to TxtMarkdownParser fallback
        return TxtMarkdownParser()


parser_factory = ParserFactory()

__all__ = [
    "BaseParser",
    "PDFParser",
    "DocxParser",
    "TxtMarkdownParser",
    "HTMLParser",
    "CodeParser",
    "ImageOCRParser",
    "ParserFactory",
    "parser_factory",
]
