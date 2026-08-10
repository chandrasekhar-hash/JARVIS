"""
Claim Extraction Engine for J.A.R.V.I.S. I2.2 V10.
"""
import re
import uuid
from typing import List, Tuple
from intelligence.web.verification.models import ClaimType, ExtractedClaim


class ClaimExtractor:
    """
    Parses draft answer text into sentences and extracts evidence-dependent claims.
    """

    CONVERSATIONAL_PATTERNS = [
        r"^(sure|hello|hi|here is|here are|i hope|let me know|feel free|in my opinion|i think|as an ai)\b",
        r"^(is there anything else|do you need|thank you|thanks)\b",
    ]

    NUMERIC_RE = re.compile(r"\b(?:\$?\d+(?:\.\d+)?%?|v?\d+\.\d+(?:\.\d+)?)\b")

    def extract_claims(self, draft_text: str) -> List[ExtractedClaim]:
        if not draft_text or not draft_text.strip():
            return []

        # Split into sentences
        raw_sentences = re.split(r"(?<=[.!?])\s+", draft_text.strip())
        claims: List[ExtractedClaim] = []

        for idx, sentence in enumerate(raw_sentences):
            sentence_clean = sentence.strip()
            if not sentence_clean:
                continue

            claim_type = self.classify_claim_type(sentence_clean)

            # Skip non-factual claims (OPINION, INSTRUCTION, UNCERTAINTY)
            if claim_type in (ClaimType.OPINION, ClaimType.INSTRUCTION, ClaimType.UNCERTAINTY):
                continue

            # Extract entities and numerics
            numerics = self.NUMERIC_RE.findall(sentence_clean)
            entities = re.findall(r"\b[A-Z][a-zA-Z0-9_\-\.]{2,30}\b", sentence_clean)

            claims.append(
                ExtractedClaim(
                    claim_id=f"claim_{uuid.uuid4().hex[:10]}",
                    text=sentence_clean,
                    claim_type=claim_type,
                    sentence_index=idx,
                    extracted_entities=list(set(entities)),
                    extracted_numerics=list(set(numerics)),
                )
            )

        return claims

    def classify_claim_type(self, sentence: str) -> ClaimType:
        s_lower = sentence.lower()

        # Check conversational / opinion
        for pat in self.CONVERSATIONAL_PATTERNS:
            if re.search(pat, s_lower):
                return ClaimType.OPINION

        if any(w in s_lower for w in ["maybe", "possibly", "uncertain", "not sure", "unclear"]):
            return ClaimType.UNCERTAINTY

        if any(w in s_lower for w in ["please", "click", "run", "execute", "install"]):
            return ClaimType.INSTRUCTION

        # Check temporal
        if any(w in s_lower for w in ["released", "announced", "in 20", "in 19", "current", "latest", "updated", "yesterday", "today", "date"]):
            return ClaimType.TEMPORAL_CLAIM

        # Check numeric/version/price
        if self.NUMERIC_RE.search(sentence):
            return ClaimType.NUMERIC_CLAIM

        # Check relationship
        if any(w in s_lower for w in ["maintains", "developed", "owns", "acquired", "depends on", "built with", "located in"]):
            return ClaimType.RELATIONSHIP_CLAIM

        # Check entity
        if re.search(r"\b[A-Z][a-zA-Z0-9_\-\.]{2,30}\b", sentence):
            return ClaimType.ENTITY_CLAIM

        return ClaimType.FACTUAL_CLAIM


claim_extractor = ClaimExtractor()
