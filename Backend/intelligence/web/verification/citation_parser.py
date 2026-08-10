"""
Strict Citation Parsing Engine for J.A.R.V.I.S. I2.2 V10.
"""
import re
import uuid
from typing import Dict, List, Optional
from intelligence.web.verification.models import (
    CitationItem,
    CitationVerificationStatus,
    EvidenceItem,
)


class CitationParser:
    """
    Parses inline citations from text and maps them to verified evidence sources.
    Enforces fail-closed rules:
    - [source_1] -> valid internal source ID
    - [1] -> valid ONLY if numeric mapping exists in evidence
    - [https://...] -> resolved against verified evidence URL, never trusted blindly
    - Unknown/ambiguous -> INVALID / FORGED
    """

    CITATION_RE = re.compile(r"\[([a-zA-Z0-9_\-\.\:\/]+)\]")

    def parse_citations(
        self,
        claim_text: str,
        evidence_registry: Dict[str, EvidenceItem],
        url_to_source_map: Optional[Dict[str, str]] = None,
        numeric_citation_map: Optional[Dict[str, str]] = None,
    ) -> List[CitationItem]:
        matches = self.CITATION_RE.findall(claim_text)
        items: List[CitationItem] = []

        url_map = url_to_source_map or {}
        num_map = numeric_citation_map or {}

        for match_str in matches:
            raw_text = f"[{match_str}]"
            item_id = f"cit_{uuid.uuid4().hex[:8]}"

            # 1. Check if direct source_id (e.g. source_1, v3_src_a1b2)
            if match_str in evidence_registry or any(ev.source_id == match_str for ev in evidence_registry.values()):
                # Resolve matching source_id
                target_ev = evidence_registry.get(match_str)
                if not target_ev:
                    target_ev = next((ev for ev in evidence_registry.values() if ev.source_id == match_str), None)

                if target_ev:
                    items.append(
                        CitationItem(
                            citation_id=item_id,
                            raw_text=raw_text,
                            source_id=target_ev.source_id,
                            canonical_url=target_ev.canonical_url,
                            source_path=target_ev.source_path,
                            is_parsed=True,
                            resolution_status=CitationVerificationStatus.VALID,
                        )
                    )
                    continue

            # 2. Check if numeric citation (e.g. [1], [2])
            if match_str.isdigit():
                target_sid = num_map.get(match_str)
                if target_sid and target_sid in evidence_registry:
                    target_ev = evidence_registry[target_sid]
                    items.append(
                        CitationItem(
                            citation_id=item_id,
                            raw_text=raw_text,
                            source_id=target_ev.source_id,
                            canonical_url=target_ev.canonical_url,
                            source_path=target_ev.source_path,
                            is_parsed=True,
                            resolution_status=CitationVerificationStatus.VALID,
                        )
                    )
                    continue
                else:
                    # Unmapped numeric citation -> FORGED
                    items.append(
                        CitationItem(
                            citation_id=item_id,
                            raw_text=raw_text,
                            is_parsed=False,
                            resolution_status=CitationVerificationStatus.FORGED,
                        )
                    )
                    continue

            # 3. Check if URL citation (e.g. [https://react.dev])
            if match_str.startswith("http://") or match_str.startswith("https://"):
                target_sid = url_map.get(match_str)
                if target_sid and target_sid in evidence_registry:
                    target_ev = evidence_registry[target_sid]
                    items.append(
                        CitationItem(
                            citation_id=item_id,
                            raw_text=raw_text,
                            source_id=target_ev.source_id,
                            canonical_url=target_ev.canonical_url,
                            source_path=target_ev.source_path,
                            is_parsed=True,
                            resolution_status=CitationVerificationStatus.VALID,
                        )
                    )
                    continue
                else:
                    # Unverified URL string -> INVALID / FORGED
                    items.append(
                        CitationItem(
                            citation_id=item_id,
                            raw_text=raw_text,
                            canonical_url=match_str,
                            is_parsed=False,
                            resolution_status=CitationVerificationStatus.INVALID,
                        )
                    )
                    continue

            # 4. Unknown / ambiguous citation format
            items.append(
                CitationItem(
                    citation_id=item_id,
                    raw_text=raw_text,
                    is_parsed=False,
                    resolution_status=CitationVerificationStatus.INVALID,
                )
            )

        return items


citation_parser = CitationParser()
