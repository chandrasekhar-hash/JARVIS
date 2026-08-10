"""
Response Sanitizer Engine for J.A.R.V.I.S. I2.2 V10.
"""
from typing import Dict, List, Optional
from intelligence.web.verification.models import (
    ClaimVerificationStatus,
    CitationVerificationStatus,
    VerifiedClaim,
)


class ResponseSanitizer:
    """
    Sanitizes draft answers by removing unsupported claims and invalid citations while
    preserving explicit multi-source evidence contradictions.
    """

    def sanitize_answer(
        self,
        draft_answer: str,
        verified_claims: List[VerifiedClaim],
        failed_claims: List[VerifiedClaim],
    ) -> str:
        if not draft_answer:
            return ""

        sanitized_sentences: List[str] = []
        all_claims = verified_claims + failed_claims
        all_claims.sort(key=lambda vc: vc.claim.sentence_index)

        for vc in all_claims:
            # 1. Repaired text if available
            if vc.repaired_text:
                sanitized_sentences.append(vc.repaired_text)
                continue

            # 2. Preserved genuine contradictions
            if vc.verification_status == ClaimVerificationStatus.CONTRADICTED:
                # If supported by competing evidence findings, preserve explicit contradiction
                competing = [f for f in vc.findings if f.finding_type == "RELATIONSHIP_CONFLICT" or "competing" in f.description.lower()]
                if competing:
                    sanitized_sentences.append(f"{vc.claim.text} (Note: Evidence is conflicting across sources.)")
                    continue
                else:
                    # Single unsupported contradiction -> omit
                    continue

            # 3. Partially supported / citation mismatch -> qualify sentence
            if vc.verification_status in (ClaimVerificationStatus.PARTIALLY_SUPPORTED, ClaimVerificationStatus.CITATION_MISMATCH):
                clean_text = self._strip_invalid_citations(vc.claim.text, vc.claim.citations)
                sanitized_sentences.append(clean_text)
                continue

            # 4. Fully supported -> keep with clean citations
            if vc.verification_status == ClaimVerificationStatus.SUPPORTED:
                clean_text = self._strip_invalid_citations(vc.claim.text, vc.claim.citations)
                sanitized_sentences.append(clean_text)
                continue

            # 5. Unsupported / Provenance invalid -> omit sentence
            if vc.verification_status in (ClaimVerificationStatus.UNSUPPORTED, ClaimVerificationStatus.PROVENANCE_INVALID, ClaimVerificationStatus.UNVERIFIED):
                continue

        if not sanitized_sentences:
            return ""

        return " ".join(sanitized_sentences)

    def _strip_invalid_citations(self, text: str, citations: List) -> str:
        clean = text
        for cit in citations:
            if cit.resolution_status in (CitationVerificationStatus.INVALID, CitationVerificationStatus.FORGED):
                clean = clean.replace(cit.raw_text, "")
        return " ".join(clean.split())


response_sanitizer = ResponseSanitizer()
