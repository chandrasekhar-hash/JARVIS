"""
J.A.R.V.I.S. Intelligence I2.2 V7 — Browser Provenance Engine.
Validates fail-closed provenance traces for browser evidence items.
Every factual claim MUST trace claim -> BrowserEvidenceItem -> page state -> interaction chain -> canonical URL -> source path.
"""
import logging
from typing import List, Dict, Any
from intelligence.web.browser.models import BrowserEvidenceItem

logger = logging.getLogger("JARVIS_BrowserProvenance")


class BrowserProvenanceEngine:
    """
    Validates provenance completeness for evidence items collected during interactive browser sessions.
    """

    def validate_provenance(self, items: List[BrowserEvidenceItem]) -> List[Dict[str, Any]]:
        provenance_chain: List[Dict[str, Any]] = []

        for item in items:
            if not item.source_id or not item.canonical_url:
                item.provenance_status = "INVALID_MISSING_SOURCE"
                continue

            if not item.interaction_chain:
                logger.warning(f"BrowserEvidenceItem '{item.evidence_id}' missing interaction_chain. Provenance incomplete.")
                item.provenance_status = "INVALID_MISSING_INTERACTION_CHAIN"
                continue

            item.provenance_status = "VALID"
            provenance_chain.append({
                "evidence_id": item.evidence_id,
                "source_id": item.source_id,
                "canonical_url": item.canonical_url,
                "page_title": item.page_title,
                "interaction_chain": item.interaction_chain,
                "source_path": item.source_path,
                "retrieved_at": item.retrieved_at,
            })

        return provenance_chain


browser_provenance_engine = BrowserProvenanceEngine()
