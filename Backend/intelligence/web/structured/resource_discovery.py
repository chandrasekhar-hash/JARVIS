"""
J.A.R.V.I.S. Intelligence I2.2 V6 — Resource Discovery & CSV Parser.
Discovers downloadable resources (.pdf, .csv, .json, .xml, .zip) from safe web pages.
Discovery DOES NOT automatically fetch resources. Reuses V2 UrlSafetyValidator.
PDF resources are handed off to I2.3 Document Intelligence. Simple CSVs are parsed under strict bounds.
"""
import csv
import io
import logging
from typing import List, Dict, Any, Tuple, Optional
from bs4 import BeautifulSoup

from intelligence.web.url_validator import url_validator
from intelligence.web.structured.models import (
    ResourceCandidate,
    StructuredDataset,
    StructuredRecord,
    StructuredField,
    StructuredDataType,
    LinkRejectionReason,
    StructuredConfig,
)

logger = logging.getLogger("JARVIS_ResourceDiscovery")

MIME_TYPE_MAP = {
    ".pdf": "application/pdf",
    ".csv": "text/csv",
    ".json": "application/json",
    ".xml": "application/xml",
    ".rss": "application/rss+xml",
    ".atom": "application/atom+xml",
    ".zip": "application/zip",
}


class ResourceDiscoveryService:
    """
    Discovers linked downloadable resources on safely retrieved pages and parses simple CSV datasets safely.
    """

    async def discover_resources(
        self, html_content: str, source_id: str, canonical_url: str
    ) -> List[ResourceCandidate]:
        candidates: List[ResourceCandidate] = []
        if not html_content or not html_content.strip():
            return candidates

        soup = BeautifulSoup(html_content, "html.parser")
        anchor_tags = soup.find_all("a", href=True)

        for a_tag in anchor_tags:
            if len(candidates) >= StructuredConfig.MAX_RESOURCES:
                break

            href = a_tag["href"].strip()
            anchor_text = a_tag.get_text(" ", strip=True)

            # Resolve relative URL
            from urllib.parse import urljoin
            target_url = urljoin(canonical_url, href)

            # Determine resource type by extension
            res_type, mime_type = self._detect_resource_type(target_url)
            if not res_type:
                continue

            # Run V2 SSRF Safety Validation asynchronously
            is_safe, resolved_ip, err_msg = await url_validator.validate_url(target_url)
            rejection_reason = LinkRejectionReason.NONE
            if not is_safe:
                err_lower = (err_msg or "").lower()
                if "encoding" in err_lower or "hex" in err_lower or "integer" in err_lower:
                    rejection_reason = LinkRejectionReason.IP_ENCODED
                elif "localhost" in err_lower or "private" in err_lower or "loopback" in err_lower or "127.0.0.1" in err_lower:
                    rejection_reason = LinkRejectionReason.LOOPBACK_OR_PRIVATE
                else:
                    rejection_reason = LinkRejectionReason.SSRF_BLOCKED

            handoff_target = None
            if res_type == "PDF":
                handoff_target = "I2.3_DOCUMENT_INTELLIGENCE"

            candidate = ResourceCandidate(
                url=target_url,
                canonical_url=target_url,
                resource_type=res_type,
                mime_type=mime_type,
                anchor_text=anchor_text,
                source_id=source_id,
                is_url_safe=is_safe,
                is_eligible=is_safe and rejection_reason == LinkRejectionReason.NONE,
                rejection_reason=rejection_reason,
                handoff_target=handoff_target,
            )
            candidates.append(candidate)

        return candidates

    def _detect_resource_type(self, url: str) -> Tuple[Optional[str], str]:
        url_lower = url.lower()
        for ext, mime in MIME_TYPE_MAP.items():
            if url_lower.endswith(ext) or f"{ext}?" in url_lower:
                return ext[1:].upper(), mime
        return None, "application/octet-stream"

    def parse_bounded_csv(
        self, csv_content_bytes: bytes, source_id: str, canonical_url: str, content_type: str = ""
    ) -> StructuredDataset:
        """
        Parses a CSV dataset with hard bounds (MAX_CSV_BYTES, MAX_CSV_ROWS, MAX_CSV_COLUMNS, MAX_CSV_CELL_LENGTH).
        Validates Content-Type to reject MIME mismatches.
        """
        if content_type and "text/csv" not in content_type.lower() and "application/csv" not in content_type.lower() and "text/plain" not in content_type.lower():
            return StructuredDataset(
                dataset_id=f"csv_ds_{source_id}",
                title="CSV Dataset",
                source_id=source_id,
                canonical_url=canonical_url,
                data_type=StructuredDataType.DATASET,
                truncated=True,
                truncation_reason=f"Content-Type mismatch: {content_type}",
            )

        trunc_reasons = []
        if len(csv_content_bytes) > StructuredConfig.MAX_CSV_BYTES:
            csv_content_bytes = csv_content_bytes[: StructuredConfig.MAX_CSV_BYTES]
            is_truncated = True
            trunc_reasons.append(f"MAX_CSV_BYTES limit ({StructuredConfig.MAX_CSV_BYTES} bytes) exceeded")
        else:
            is_truncated = False

        text = csv_content_bytes.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))

        rows: List[List[str]] = []
        for r_idx, row in enumerate(reader):
            if r_idx >= StructuredConfig.MAX_CSV_ROWS:
                is_truncated = True
                trunc_reasons.append(f"MAX_CSV_ROWS limit ({StructuredConfig.MAX_CSV_ROWS}) reached")
                break

            capped_row = []
            for c_idx, cell in enumerate(row):
                if c_idx >= StructuredConfig.MAX_CSV_COLUMNS:
                    break
                if len(cell) > StructuredConfig.MAX_CSV_CELL_LENGTH:
                    cell = cell[: StructuredConfig.MAX_CSV_CELL_LENGTH] + "...[TRUNCATED]"
                    is_truncated = True
                capped_row.append(cell)

            rows.append(capped_row)

        headers = rows[0] if rows else []
        data_rows = rows[1:] if len(rows) > 1 else []

        records: List[StructuredRecord] = []
        for r_idx, row in enumerate(data_rows):
            fields: List[StructuredField] = []
            for c_idx, val in enumerate(row):
                col_name = headers[c_idx] if c_idx < len(headers) else f"Column {c_idx + 1}"
                source_path = f"csv.row[{r_idx}].column[\"{col_name}\"]"
                fields.append(
                    StructuredField(
                        name=col_name,
                        value=val,
                        source_path=source_path,
                        source_id=source_id,
                    )
                )

            record = StructuredRecord(
                record_id=f"csv_{source_id}_{r_idx}",
                record_type=StructuredDataType.DATASET,
                fields=fields,
                source_id=source_id,
                canonical_url=canonical_url,
                extraction_method="BOUNDED_CSV",
            )
            records.append(record)

        return StructuredDataset(
            dataset_id=f"csv_ds_{source_id}",
            title="CSV Dataset",
            columns=headers,
            records=records,
            source_id=source_id,
            canonical_url=canonical_url,
            data_type=StructuredDataType.DATASET,
            truncated=is_truncated,
            truncation_reason="; ".join(trunc_reasons) if trunc_reasons else None,
            total_records_detected=len(rows),
            records_returned=len(records),
        )


resource_discovery_service = ResourceDiscoveryService()
