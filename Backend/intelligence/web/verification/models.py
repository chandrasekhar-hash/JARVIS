"""
Data Models and Categorical Enums for J.A.R.V.I.S. I2.2 V10 Grounded Answer Verification.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any


class ClaimVerificationStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    UNSUPPORTED = "UNSUPPORTED"
    UNVERIFIED = "UNVERIFIED"
    STALE = "STALE"
    CITATION_MISMATCH = "CITATION_MISMATCH"
    PROVENANCE_INVALID = "PROVENANCE_INVALID"


class CitationVerificationStatus(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    MISSING = "MISSING"
    MISMATCHED = "MISMATCHED"
    FORGED = "FORGED"


class AnswerVerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIAL = "PARTIAL"
    REQUIRES_REPAIR = "REQUIRES_REPAIR"
    CONTRADICTED = "CONTRADICTED"
    REJECTED = "REJECTED"
    NO_GROUNDED_EVIDENCE = "NO_GROUNDED_EVIDENCE"


class ClaimType(str, Enum):
    FACTUAL_CLAIM = "FACTUAL_CLAIM"
    TEMPORAL_CLAIM = "TEMPORAL_CLAIM"
    ENTITY_CLAIM = "ENTITY_CLAIM"
    RELATIONSHIP_CLAIM = "RELATIONSHIP_CLAIM"
    NUMERIC_CLAIM = "NUMERIC_CLAIM"
    OPINION = "OPINION"
    INSTRUCTION = "INSTRUCTION"
    UNCERTAINTY = "UNCERTAINTY"


class EvidenceMatchStatus(str, Enum):
    DIRECTLY_SUPPORTED = "DIRECTLY_SUPPORTED"
    SUPPORTED_BY_MULTIPLE_SOURCES = "SUPPORTED_BY_MULTIPLE_SOURCES"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    NO_SUPPORT_FOUND = "NO_SUPPORT_FOUND"


@dataclass
class EvidenceItem:
    evidence_id: str
    source_id: str
    canonical_url: Optional[str] = None
    source_path: Optional[str] = None
    provenance_status: str = "VERIFIED"
    text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source_id": self.source_id,
            "canonical_url": self.canonical_url,
            "source_path": self.source_path,
            "provenance_status": self.provenance_status,
            "text": self.text,
            "metadata": self.metadata,
        }


@dataclass
class CitationItem:
    citation_id: str
    raw_text: str
    source_id: Optional[str] = None
    canonical_url: Optional[str] = None
    source_path: Optional[str] = None
    is_parsed: bool = False
    resolution_status: CitationVerificationStatus = CitationVerificationStatus.MISSING

    def to_dict(self) -> Dict[str, Any]:
        return {
            "citation_id": self.citation_id,
            "raw_text": self.raw_text,
            "source_id": self.source_id,
            "canonical_url": self.canonical_url,
            "source_path": self.source_path,
            "is_parsed": self.is_parsed,
            "resolution_status": self.resolution_status.value,
        }


@dataclass
class ExtractedClaim:
    claim_id: str
    text: str
    claim_type: ClaimType
    sentence_index: int
    citations: List[CitationItem] = field(default_factory=list)
    extracted_entities: List[str] = field(default_factory=list)
    extracted_numerics: List[str] = field(default_factory=list)
    temporal_context: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "text": self.text,
            "claim_type": self.claim_type.value,
            "sentence_index": self.sentence_index,
            "citations": [c.to_dict() for c in self.citations],
            "extracted_entities": self.extracted_entities,
            "extracted_numerics": self.extracted_numerics,
            "temporal_context": self.temporal_context,
        }


@dataclass
class VerificationFinding:
    finding_id: str
    claim_id: str
    finding_type: str
    description: str
    competing_evidence: List[Dict[str, Any]] = field(default_factory=list)
    suggested_action: str = "QUALIFY"  # REMOVE, QUALIFY, REPAIR, OMIT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "claim_id": self.claim_id,
            "finding_type": self.finding_type,
            "description": self.description,
            "competing_evidence": self.competing_evidence,
            "suggested_action": self.suggested_action,
        }


@dataclass
class VerifiedClaim:
    claim: ExtractedClaim
    verification_status: ClaimVerificationStatus
    citation_status: CitationVerificationStatus
    evidence_match_status: EvidenceMatchStatus
    evidence_ids: List[str] = field(default_factory=list)
    source_ids: List[str] = field(default_factory=list)
    canonical_urls: List[str] = field(default_factory=list)
    findings: List[VerificationFinding] = field(default_factory=list)
    repaired_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim": self.claim.to_dict(),
            "verification_status": self.verification_status.value,
            "citation_status": self.citation_status.value,
            "evidence_match_status": self.evidence_match_status.value,
            "evidence_ids": self.evidence_ids,
            "source_ids": self.source_ids,
            "canonical_urls": self.canonical_urls,
            "findings": [f.to_dict() for f in self.findings],
            "repaired_text": self.repaired_text,
        }


@dataclass
class VerificationWebRequest:
    draft_answer: str
    evidence_context: List[Dict[str, Any]] = field(default_factory=list)
    query: str = ""
    conversation_id: Optional[str] = None
    owner_scope_id: Optional[str] = None
    user_timezone: Optional[str] = None


@dataclass
class VerificationWebResponse:
    verification_status: AnswerVerificationStatus
    verified_claims: List[VerifiedClaim] = field(default_factory=list)
    failed_claims: List[VerifiedClaim] = field(default_factory=list)
    citation_results: List[Dict[str, Any]] = field(default_factory=list)
    findings: List[VerificationFinding] = field(default_factory=list)
    repair_status: str = "NONE"  # NONE, REPAIRED, REPAIR_FAILED
    provenance_status: str = "VERIFIED"
    grounding_status: str = "GROUNDED"
    sanitized_answer: str = ""
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verification_status": self.verification_status.value,
            "verified_claims": [c.to_dict() for c in self.verified_claims],
            "failed_claims": [c.to_dict() for c in self.failed_claims],
            "citation_results": self.citation_results,
            "findings": [f.to_dict() for f in self.findings],
            "repair_status": self.repair_status,
            "provenance_status": self.provenance_status,
            "grounding_status": self.grounding_status,
            "sanitized_answer": self.sanitized_answer,
            "warnings": self.warnings,
        }
