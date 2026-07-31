"""
JARVIS Product 1.6 - Document Ingestion Pipeline.
Handles validation, normalization, parsing, and chunk generation.
"""

import os
import hashlib
import unicodedata
import re
import logging
from typing import Tuple, List, Dict, Any, Optional
from .parsers import parser_factory, BaseParser
from .chunking import ChunkingEngine
from .models import Document, Chunk, DocumentType, DocumentPermissions

logger = logging.getLogger(__name__)


class FileValidator:
    MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB limit

    @classmethod
    def validate_file(cls, file_path: str) -> Tuple[bool, str, str]:
        """Returns (is_valid, checksum, mime_type_guess)"""
        if not os.path.exists(file_path):
            return False, "", "File not found"

        size = os.path.getsize(file_path)
        if size > cls.MAX_FILE_SIZE_BYTES:
            return False, "", f"File size ({size} bytes) exceeds limit (50MB)"

        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        checksum = hasher.hexdigest()

        ext = os.path.splitext(file_path)[1].lower()
        return True, checksum, ext


class TextNormalizer:
    @classmethod
    def normalize(cls, raw_text: str) -> str:
        if not raw_text:
            return ""

        # Unicode NFKC normalization
        normalized = unicodedata.normalize("NFKC", raw_text)
        # Standardize line breaks
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
        # Strip non-printable control characters except tab and newline
        normalized = "".join([ch for ch in normalized if ch in ("\n", "\t") or unicodedata.category(ch)[0] != "C"])
        # Collapse excessive blank lines
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()


class IngestionPipeline:
    def __init__(self, chunker: Optional[ChunkingEngine] = None):
        self.chunker = chunker or ChunkingEngine()

    def process_file(
        self,
        file_path: str,
        title: str,
        owner_id: str,
        tags: Optional[List[str]] = None,
        permissions: Optional[DocumentPermissions] = None,
    ) -> Tuple[Document, List[Chunk]]:
        is_valid, checksum, ext_guess = FileValidator.validate_file(file_path)
        if not is_valid:
            raise ValueError(f"File validation failed: {ext_guess}")

        # Select Parser
        parser: BaseParser = parser_factory.get_parser(file_path)
        raw_text, parse_metadata = parser.parse(file_path)

        # Normalize Text
        clean_text = TextNormalizer.normalize(raw_text)

        # Map Document Type
        doc_type = DocumentType.TXT
        if ext_guess in (".pdf",):
            doc_type = DocumentType.PDF
        elif ext_guess in (".docx", ".doc"):
            doc_type = DocumentType.DOCX
        elif ext_guess in (".md", ".markdown"):
            doc_type = DocumentType.MARKDOWN
        elif ext_guess in (".html", ".htm"):
            doc_type = DocumentType.HTML
        elif ext_guess in (".png", ".jpg", ".jpeg", ".webp"):
            doc_type = DocumentType.IMAGE_OCR
        elif ext_guess in (".py", ".js", ".ts", ".cpp", ".rs", ".go", ".json", ".sql"):
            doc_type = DocumentType.CODE

        # Create Document Object
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else len(clean_text)
        doc = Document.create_new(
            title=title or os.path.basename(file_path),
            owner=owner_id,
            source=file_path,
            document_type=doc_type,
            checksum=checksum,
            tags=tags,
            permissions=permissions,
            file_size_bytes=file_size,
            custom_metadata=parse_metadata,
        )

        # Generate Chunks
        chunks = self.chunker.chunk_text(
            document_id=doc.document_id,
            text=clean_text,
            chunk_size=512,
            overlap=64,
            section_title=title,
        )

        doc.total_chunks = len(chunks)
        return doc, chunks
