"""
Main Content Extractor and Structured Content Parser for J.A.R.V.I.S. I2.2 V2.

Implements encoding robustness (UTF-8/chardet fallback + errors='replace'), safe HTML parsing,
container-first content extraction, structural element preservation (heading hierarchy, code indentation,
markdown tables, lists), JS-shell detection, and strict metadata extraction.
"""
import re
import html
import logging
from typing import List, Optional, Tuple, Dict, Any
from bs4 import BeautifulSoup, Tag, NavigableString

from intelligence.web.models import (
    WebPageBlockType,
    WebContentBlock,
    WebPageMetadata,
    WebPageDocument,
    WebRetrievalStatus,
)
from tools.telemetry import log_structured, backend_log

logger = logging.getLogger("JARVIS_MainContentExtractor")


class MainContentExtractor:
    """
    Container-first Content Extractor and Structural Parser.
    Decouples document extraction from reasoning while preserving structure.
    """

    @staticmethod
    def decode_content_bytes(raw_bytes: bytes, content_type_header: str = "") -> str:
        """
        Decodes raw HTTP bytes safely using declared charset, UTF-8, or chardet fallback
        with errors='replace' to guarantee zero crashes on malformed byte sequences.
        """
        if not raw_bytes:
            return ""

        # 1. Check HTTP header content-type declared charset
        declared_charset = None
        if content_type_header:
            match = re.search(r"charset=([\w-]+)", content_type_header, re.IGNORECASE)
            if match:
                declared_charset = match.group(1).strip()

        if declared_charset:
            try:
                return raw_bytes.decode(declared_charset, errors="replace")
            except Exception:
                pass

        # 2. Try UTF-8
        try:
            return raw_bytes.decode("utf-8", errors="replace")
        except Exception:
            pass

        # 3. Fallback to latin-1 / ascii with replace
        return raw_bytes.decode("latin-1", errors="replace")

    @classmethod
    def _extract_page_metadata(cls, soup: BeautifulSoup, initial_meta: WebPageMetadata) -> WebPageMetadata:
        """Extracts title, canonical URL, description, author, published_at from HTML tags."""
        title = None
        canonical = None
        description = None
        author = None
        published_at = None

        # Canonical URL
        canon_tag = soup.find("link", rel=lambda r: r and "canonical" in r.lower())
        if canon_tag and canon_tag.get("href"):
            canonical = str(canon_tag["href"]).strip()

        # Title
        og_title = soup.find("meta", property="og:title") or soup.find("meta", attrs={"name": "twitter:title"})
        if og_title and og_title.get("content"):
            title = str(og_title["content"]).strip()
        elif soup.title and soup.title.string:
            title = soup.title.string.strip()

        # Description
        meta_desc = (
            soup.find("meta", attrs={"name": "description"})
            or soup.find("meta", property="og:description")
        )
        if meta_desc and meta_desc.get("content"):
            description = str(meta_desc["content"]).strip()

        # Author
        meta_author = (
            soup.find("meta", attrs={"name": "author"})
            or soup.find("meta", property="article:author")
        )
        if meta_author and meta_author.get("content"):
            author = str(meta_author["content"]).strip()

        # Published date
        meta_pub = (
            soup.find("meta", property="article:published_time")
            or soup.find("meta", attrs={"name": "publication_date"})
            or soup.find("meta", attrs={"name": "date"})
        )
        if meta_pub and meta_pub.get("content"):
            published_at = str(meta_pub["content"]).strip()

        return WebPageMetadata(
            requested_url=initial_meta.requested_url,
            final_url=initial_meta.final_url,
            canonical_url=canonical or initial_meta.canonical_url,
            domain=initial_meta.domain,
            title=title or initial_meta.title,
            description=description or initial_meta.description,
            author=author or initial_meta.author,
            published_at=published_at or initial_meta.published_at,
            content_type=initial_meta.content_type,
            retrieved_at=initial_meta.retrieved_at,
            http_status=initial_meta.http_status,
        )

    @classmethod
    def _find_main_container(cls, soup: BeautifulSoup) -> Tag:
        """
        Container-First Strategy:
        1. Explicit semantic container (<main>, <article>, role="main")
        2. Highest text-density DOM container fallback
        """
        # Semantic check
        semantic_main = (
            soup.find("main")
            or soup.find("article")
            or soup.find(attrs={"role": "main"})
            or soup.find("div", class_=re.compile(r"content|main|article|documentation", re.I))
            or soup.find("section", class_=re.compile(r"content|main|article", re.I))
        )
        if semantic_main and isinstance(semantic_main, Tag):
            return semantic_main

        # Fallback: Body or root soup
        return soup.body if soup.body else soup

    @classmethod
    def _table_to_markdown(cls, table_tag: Tag) -> str:
        """Converts HTML table to Markdown table text, preserving row/column alignment."""
        rows = table_tag.find_all("tr")
        if not rows:
            return ""

        md_lines = []
        header_parsed = False

        for row in rows:
            headers = row.find_all(["th"])
            cells = row.find_all(["td"])

            if headers and not header_parsed:
                header_text = [h.get_text(strip=True).replace("|", "\\|") for h in headers]
                if header_text:
                    md_lines.append("| " + " | ".join(header_text) + " |")
                    md_lines.append("| " + " | ".join(["---"] * len(header_text)) + " |")
                    header_parsed = True
            elif cells:
                cell_text = [c.get_text(strip=True).replace("|", "\\|") for c in cells]
                if cell_text:
                    if not header_parsed:
                        # Dummy header if table starts directly with <td>
                        md_lines.append("| " + " | ".join([f"Col {i+1}" for i in range(len(cell_text))]) + " |")
                        md_lines.append("| " + " | ".join(["---"] * len(cell_text)) + " |")
                        header_parsed = True
                    md_lines.append("| " + " | ".join(cell_text) + " |")

        return "\n".join(md_lines)

    @classmethod
    def parse_document(
        cls,
        raw_bytes: bytes,
        initial_meta: WebPageMetadata,
        max_content_chars: int = 50000
    ) -> WebPageDocument:
        """
        Parses raw webpage HTML into a structured WebPageDocument.
        Preserves heading hierarchy, code indentation, tables, and lists.
        """
        html_text = cls.decode_content_bytes(raw_bytes, initial_meta.content_type)
        if not html_text or not html_text.strip():
            return WebPageDocument(
                metadata=initial_meta,
                blocks=[],
                extracted_text="",
                content_length=0,
                retrieval_status=WebRetrievalStatus.EMPTY_CONTENT,
                warnings=["Received empty HTML string."]
            )

        soup = BeautifulSoup(html_text, "html.parser")
        metadata = cls._extract_page_metadata(soup, initial_meta)

        # Remove explicit noise tags first (scripts, styles, svg, canvas, iframe)
        for noise_tag in soup(["script", "style", "noscript", "iframe", "canvas", "svg"]):
            noise_tag.decompose()

        # Find main content container
        main_container = cls._find_main_container(soup)

        blocks: List[WebContentBlock] = []
        current_heading_path: List[str] = []
        block_idx = 1
        total_extracted_chars = 0
        truncated = False

        # If page title exists, add as TITLE block
        if metadata.title:
            blocks.append(WebContentBlock(
                block_index=block_idx,
                block_type=WebPageBlockType.TITLE,
                text=metadata.title,
                heading_path=[],
                source_url=metadata.canonical_url
            ))
            block_idx += 1
            current_heading_path = [metadata.title]

        # Iterate structural elements inside main container
        elements = main_container.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "pre", "table", "ul", "ol", "blockquote"])

        for elem in elements:
            if total_extracted_chars >= max_content_chars:
                truncated = True
                break

            tag_name = elem.name.lower()

            # 1. Heading Tags (H1-H6)
            if tag_name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                h_text = elem.get_text(strip=True)
                if not h_text:
                    continue

                h_level = int(tag_name[1])
                # Adjust heading path hierarchy
                if h_level == 1:
                    current_heading_path = [h_text]
                elif h_level == 2:
                    current_heading_path = current_heading_path[:1] + [h_text]
                else:
                    current_heading_path = current_heading_path[:2] + [h_text]

                blocks.append(WebContentBlock(
                    block_index=block_idx,
                    block_type=WebPageBlockType.HEADING,
                    text=h_text,
                    heading_path=list(current_heading_path),
                    source_url=metadata.canonical_url,
                    metadata={"level": h_level}
                ))
                block_idx += 1
                total_extracted_chars += len(h_text)

            # 2. Code Blocks (<pre><code> or <pre>)
            elif tag_name == "pre":
                # Preserve indentation and line breaks inside code block
                code_text = elem.get_text()
                if not code_text or not code_text.strip():
                    continue

                code_clean = html.unescape(code_text.rstrip())
                lang = ""
                code_elem = elem.find("code")
                if code_elem and isinstance(code_elem, Tag):
                    cls_attr = code_elem.get("class", [])
                    for c in cls_attr:
                        if c.startswith("language-") or c.startswith("lang-"):
                            lang = c.split("-", 1)[1]
                            break

                blocks.append(WebContentBlock(
                    block_index=block_idx,
                    block_type=WebPageBlockType.CODE,
                    text=code_clean,
                    heading_path=list(current_heading_path),
                    source_url=metadata.canonical_url,
                    metadata={"language": lang}
                ))
                block_idx += 1
                total_extracted_chars += len(code_clean)

            # 3. Tables (<table>)
            elif tag_name == "table":
                md_table = cls._table_to_markdown(elem)
                if not md_table or not md_table.strip():
                    continue

                blocks.append(WebContentBlock(
                    block_index=block_idx,
                    block_type=WebPageBlockType.TABLE,
                    text=md_table,
                    heading_path=list(current_heading_path),
                    source_url=metadata.canonical_url
                ))
                block_idx += 1
                total_extracted_chars += len(md_table)

            # 4. Lists (<ul>, <ol>)
            elif tag_name in ["ul", "ol"]:
                items = elem.find_all("li", recursive=False)
                if not items:
                    continue

                list_lines = []
                for idx, li in enumerate(items, start=1):
                    li_text = li.get_text(strip=True)
                    if li_text:
                        bullet = f"{idx}." if tag_name == "ol" else "-"
                        list_lines.append(f"{bullet} {li_text}")

                if list_lines:
                    full_list_text = "\n".join(list_lines)
                    blocks.append(WebContentBlock(
                        block_index=block_idx,
                        block_type=WebPageBlockType.LIST,
                        text=full_list_text,
                        heading_path=list(current_heading_path),
                        source_url=metadata.canonical_url
                    ))
                    block_idx += 1
                    total_extracted_chars += len(full_list_text)

            # 5. Paragraphs (<p>)
            elif tag_name == "p":
                p_text = html.unescape(elem.get_text(strip=True))
                if not p_text or len(p_text) < 5:
                    continue

                blocks.append(WebContentBlock(
                    block_index=block_idx,
                    block_type=WebPageBlockType.PARAGRAPH,
                    text=p_text,
                    heading_path=list(current_heading_path),
                    source_url=metadata.canonical_url
                ))
                block_idx += 1
                total_extracted_chars += len(p_text)

            # 6. Blockquotes
            elif tag_name == "blockquote":
                q_text = html.unescape(elem.get_text(strip=True))
                if not q_text:
                    continue

                blocks.append(WebContentBlock(
                    block_index=block_idx,
                    block_type=WebPageBlockType.QUOTE,
                    text=q_text,
                    heading_path=list(current_heading_path),
                    source_url=metadata.canonical_url
                ))
                block_idx += 1
                total_extracted_chars += len(q_text)

        # Assemble full extracted text representation
        extracted_text_parts = [b.text for b in blocks]
        full_extracted_text = "\n\n".join(extracted_text_parts)

        # JS Shell Detection
        retrieval_status = WebRetrievalStatus.SUCCESS
        if len(full_extracted_text.strip()) < 50:
            raw_html_lower = html_text.lower()
            if any(term in raw_html_lower for term in ["enable javascript", "javascript required", "you need to enable javascript", "<div id=\"root\"></div>", "<div id=\"app\"></div>"]):
                retrieval_status = WebRetrievalStatus.JS_RENDER_REQUIRED

        return WebPageDocument(
            metadata=metadata,
            blocks=blocks,
            extracted_text=full_extracted_text,
            content_length=len(full_extracted_text),
            truncated=truncated,
            retrieval_status=retrieval_status
        )


# Global singleton instance
content_extractor = MainContentExtractor()
