"""
J.A.R.V.I.S. Intelligence I2.2 V6 — Structured Web Data & Resource Intelligence.
Purely additive subpackage for structured tables, JSON, JSON-LD, feeds, lists, resources, and pagination.
"""
from intelligence.web.structured.models import (
    StructuredDataType,
    StructuredField,
    StructuredRecord,
    StructuredDataset,
    ResourceCandidate,
    PaginationMetadata,
    StructuredExtractionResult,
    StructuredWebRequest,
    StructuredWebResponse,
    StructuredConfig,
)
from intelligence.web.structured.structured_service import web_structured_service, StructuredWebService

__all__ = [
    "StructuredDataType",
    "StructuredField",
    "StructuredRecord",
    "StructuredDataset",
    "ResourceCandidate",
    "PaginationMetadata",
    "StructuredExtractionResult",
    "StructuredWebRequest",
    "StructuredWebResponse",
    "StructuredConfig",
    "web_structured_service",
    "StructuredWebService",
]
