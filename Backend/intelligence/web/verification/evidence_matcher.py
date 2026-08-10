"""
Evidence Matching Engine for J.A.R.V.I.S. I2.2 V10.
"""
import re
from typing import Dict, List, Tuple
from intelligence.web.verification.models import (
    EvidenceItem,
    EvidenceMatchStatus,
    ExtractedClaim,
)


class EvidenceMatcher:
    """
    Matches extracted claims against supplied V1-V9 evidence items using categorical classifications.
    No arbitrary numeric confidence scores.
    """

    def match_claim_against_evidence(
        self,
        claim: ExtractedClaim,
        evidence_items: List[EvidenceItem],
    ) -> Tuple[EvidenceMatchStatus, List[str], List[str], List[str]]:
        if not evidence_items:
            return EvidenceMatchStatus.NO_SUPPORT_FOUND, [], [], []

        matching_evidence_ids: List[str] = []
        matching_source_ids: List[str] = []
        matching_urls: List[str] = []
        has_partial = False
        has_direct = False
        contradicting_count = 0

        for ev in evidence_items:
            if not ev.text:
                continue

            match_type, is_contradiction = self._evaluate_text_match(claim, ev.text)
            if is_contradiction:
                contradicting_count += 1

            if match_type == "DIRECT":
                has_direct = True
                if ev.evidence_id not in matching_evidence_ids:
                    matching_evidence_ids.append(ev.evidence_id)
                if ev.source_id not in matching_source_ids:
                    matching_source_ids.append(ev.source_id)
                if ev.canonical_url and ev.canonical_url not in matching_urls:
                    matching_urls.append(ev.canonical_url)
            elif match_type == "PARTIAL":
                has_partial = True
                if ev.evidence_id not in matching_evidence_ids:
                    matching_evidence_ids.append(ev.evidence_id)
                if ev.source_id not in matching_source_ids:
                    matching_source_ids.append(ev.source_id)
                if ev.canonical_url and ev.canonical_url not in matching_urls:
                    matching_urls.append(ev.canonical_url)

        if contradicting_count > 0 and not matching_evidence_ids:
            return EvidenceMatchStatus.CONTRADICTED, [], [], []

        if len(matching_source_ids) > 1 and has_direct:
            return (
                EvidenceMatchStatus.SUPPORTED_BY_MULTIPLE_SOURCES,
                matching_evidence_ids,
                matching_source_ids,
                matching_urls,
            )

        if has_direct and len(matching_evidence_ids) >= 1:
            return (
                EvidenceMatchStatus.DIRECTLY_SUPPORTED,
                matching_evidence_ids,
                matching_source_ids,
                matching_urls,
            )

        if has_partial:
            return (
                EvidenceMatchStatus.PARTIALLY_SUPPORTED,
                matching_evidence_ids,
                matching_source_ids,
                matching_urls,
            )

        return EvidenceMatchStatus.NO_SUPPORT_FOUND, [], [], []

    def _evaluate_text_match(self, claim: ExtractedClaim, ev_text: str) -> Tuple[str, bool]:
        ev_lower = ev_text.lower()
        c_lower = claim.text.lower()

        # Check numerics/versions if claim contains numeric values
        if claim.extracted_numerics:
            for num in claim.extracted_numerics:
                if num.lower() in ev_lower:
                    return "DIRECT", False
                # If claim states a specific version/price not in evidence, check contradiction
                if re.search(r"v?\d+\.\d+", num) and re.search(r"v?\d+\.\d+", ev_text):
                    if num.lower() not in ev_lower:
                        return "NONE", True

        # Check entity correspondence
        if claim.extracted_entities:
            matched_ents = [ent for ent in claim.extracted_entities if ent.lower() in ev_lower]
            if len(matched_ents) == len(claim.extracted_entities):
                return "DIRECT", False
            if matched_ents:
                return "PARTIAL", False
            return "NONE", False

        # Fallback text substring
        c_words = set(re.findall(r"\w+", c_lower)) - {"the", "a", "an", "is", "are", "was", "were", "in", "of", "to", "for"}
        if not c_words:
            return "NONE", False

        matched_words = [w for w in c_words if w in ev_lower]
        ratio = len(matched_words) / len(c_words)
        if ratio >= 0.5:
            return "DIRECT", False
        if ratio >= 0.25:
            return "PARTIAL", False

        return "NONE", False


evidence_matcher = EvidenceMatcher()
