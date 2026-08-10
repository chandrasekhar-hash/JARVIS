"""
J.A.R.V.I.S. Intelligence I2.2 V10 — Grounded Answer Verification & Citation Intelligence Package.
"""
from intelligence.web.verification.models import (
    VerificationWebRequest,
    VerificationWebResponse,
    AnswerVerificationStatus,
    ClaimVerificationStatus,
    CitationVerificationStatus,
    ClaimType,
    EvidenceMatchStatus,
)
from intelligence.web.verification.verification_service import web_verification_service, WebVerificationService

__all__ = [
    "web_verification_service",
    "WebVerificationService",
    "VerificationWebRequest",
    "VerificationWebResponse",
    "AnswerVerificationStatus",
    "ClaimVerificationStatus",
    "CitationVerificationStatus",
    "ClaimType",
    "EvidenceMatchStatus",
]
