"""
JARVIS Product 1.6 - Chunking Engine.
Splits text into token-bounded semantic chunks with configurable overlap.
"""

import hashlib
import re
from typing import List, Optional
from .interfaces import IChunker
from .models import Chunk, ChunkLocation


class ChunkingEngine(IChunker):
    def __init__(self, default_chunk_size: int = 512, default_overlap: int = 64):
        self.default_chunk_size = default_chunk_size
        self.default_overlap = default_overlap

    def _estimate_tokens(self, text: str) -> int:
        """Approximate token count (averaging 4 chars per token)."""
        return max(1, len(text) // 4)

    def chunk_text(
        self,
        document_id: str,
        text: str,
        chunk_size: int = 512,
        overlap: int = 64,
        section_title: Optional[str] = None,
    ) -> List[Chunk]:
        if not text or not text.strip():
            return []

        chunk_size = chunk_size or self.default_chunk_size
        overlap = overlap or self.default_overlap

        # Split into semantic paragraphs first
        paragraphs = re.split(r"\n\s*\n", text)
        chunks: List[Chunk] = []

        current_chunk_words: List[str] = []
        current_token_count = 0
        chunk_idx = 0
        char_offset = 0

        for p in paragraphs:
            p_clean = p.strip()
            if not p_clean:
                continue

            p_words = p_clean.split()
            p_tokens = self._estimate_tokens(p_clean)

            if current_token_count + p_tokens <= chunk_size or not current_chunk_words:
                current_chunk_words.extend(p_words)
                current_token_count += p_tokens
            else:
                # Flush chunk
                chunk_text_str = " ".join(current_chunk_words)
                chk_checksum = hashlib.sha256(chunk_text_str.encode("utf-8")).hexdigest()
                location = ChunkLocation(
                    section_title=section_title,
                    start_offset=char_offset,
                    end_offset=char_offset + len(chunk_text_str),
                )
                chunk_obj = Chunk.create_new(
                    document_id=document_id,
                    chunk_index=chunk_idx,
                    text=chunk_text_str,
                    token_count=self._estimate_tokens(chunk_text_str),
                    location=location,
                    checksum=chk_checksum,
                )
                chunks.append(chunk_obj)
                chunk_idx += 1
                char_offset += len(chunk_text_str)

                # Maintain overlap
                overlap_words = current_chunk_words[-max(1, overlap // 4):] if overlap > 0 else []
                current_chunk_words = overlap_words + p_words
                current_token_count = self._estimate_tokens(" ".join(current_chunk_words))

        # Final chunk flush
        if current_chunk_words:
            chunk_text_str = " ".join(current_chunk_words)
            chk_checksum = hashlib.sha256(chunk_text_str.encode("utf-8")).hexdigest()
            location = ChunkLocation(
                section_title=section_title,
                start_offset=char_offset,
                end_offset=char_offset + len(chunk_text_str),
            )
            chunk_obj = Chunk.create_new(
                document_id=document_id,
                chunk_index=chunk_idx,
                text=chunk_text_str,
                token_count=self._estimate_tokens(chunk_text_str),
                location=location,
                checksum=chk_checksum,
            )
            chunks.append(chunk_obj)

        return chunks
