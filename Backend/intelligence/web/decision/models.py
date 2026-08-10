"""
Data Models and Categorical Enums for J.A.R.V.I.S. I2.2 V11 Decision, Comparison & Recommendation Intelligence.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any


class DecisionIntent(str, Enum):
    COMPARISON = "COMPARISON"
    RECOMMENDATION = "RECOMMENDATION"
    PURCHASE_DECISION = "PURCHASE_DECISION"
    TECHNOLOGY_SELECTION = "TECHNOLOGY_SELECTION"
    OPTION_RANKING = "OPTION_RANKING"
    CONSTRAINT_FILTERING = "CONSTRAINT_FILTERING"
    TRADEOFF_ANALYSIS = "TRADEOFF_ANALYSIS"
    BEST_FOR_USE_CASE = "BEST_FOR_USE_CASE"
    ALTERNATIVE_SELECTION = "ALTERNATIVE_SELECTION"
    NO_DECISION_REQUIRED = "NO_DECISION_REQUIRED"


class RequirementType(str, Enum):
    HARD_CONSTRAINT = "HARD_CONSTRAINT"
    SOFT_PREFERENCE = "SOFT_PREFERENCE"
    OPTIONAL_CRITERION = "OPTIONAL_CRITERION"
    UNKNOWN_REQUIREMENT = "UNKNOWN_REQUIREMENT"


class ConstraintType(str, Enum):
    BUDGET_MAX = "BUDGET_MAX"
    PRICE_MAX = "PRICE_MAX"
    RAM_MIN = "RAM_MIN"
    STORAGE_MIN = "STORAGE_MIN"
    VERSION_MIN = "VERSION_MIN"
    FEATURE_REQUIRED = "FEATURE_REQUIRED"
    ENTITY_MATCH = "ENTITY_MATCH"
    TIME_FRAME = "TIME_FRAME"
    CUSTOM = "CUSTOM"


class ConstraintStatus(str, Enum):
    SATISFIED = "SATISFIED"
    NOT_SATISFIED = "NOT_SATISFIED"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class DecisionStatus(str, Enum):
    DECIDED = "DECIDED"
    PARTIAL = "PARTIAL"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONFLICTING_REQUIREMENTS = "CONFLICTING_REQUIREMENTS"
    NO_RECOMMENDATION = "NO_RECOMMENDATION"


class CandidateStatus(str, Enum):
    MEETS_ALL_HARD_CONSTRAINTS = "MEETS_ALL_HARD_CONSTRAINTS"
    MEETS_MOST_REQUIREMENTS = "MEETS_MOST_REQUIREMENTS"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    FAILS_HARD_CONSTRAINT = "FAILS_HARD_CONSTRAINT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class CriterionStatus(str, Enum):
    EVIDENCE_VERIFIED = "EVIDENCE_VERIFIED"
    UNVERIFIED_EVIDENCE = "UNVERIFIED_EVIDENCE"
    STALE_EVIDENCE = "STALE_EVIDENCE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONTRADICTED_EVIDENCE = "CONTRADICTED_EVIDENCE"


class TradeoffType(str, Enum):
    PERFORMANCE_VS_BATTERY = "PERFORMANCE_VS_BATTERY"
    PRICE_VS_FEATURES = "PRICE_VS_FEATURES"
    PORTABILITY_VS_PERFORMANCE = "PORTABILITY_VS_PERFORMANCE"
    NEWER_VERSION_VS_PRICE = "NEWER_VERSION_VS_PRICE"
    FEATURES_VS_COST = "FEATURES_VS_COST"
    SUPPORT_VS_COST = "SUPPORT_VS_COST"
    CUSTOM = "CUSTOM"


class RecommendationStatus(str, Enum):
    PRIMARY_RECOMMENDATION = "PRIMARY_RECOMMENDATION"
    ALTERNATIVE_RECOMMENDATION = "ALTERNATIVE_RECOMMENDATION"
    BUDGET_ALTERNATIVE = "BUDGET_ALTERNATIVE"
    TIE = "TIE"
    NO_RECOMMENDATION = "NO_RECOMMENDATION"


class RecommendationStability(str, Enum):
    STABLE = "STABLE"
    SENSITIVE_TO_EVIDENCE = "SENSITIVE_TO_EVIDENCE"
    UNSTABLE = "UNSTABLE"


class EvidenceCoverageStatus(str, Enum):
    FULL_COVERAGE = "FULL_COVERAGE"
    PARTIAL_COVERAGE = "PARTIAL_COVERAGE"
    SPARSE_COVERAGE = "SPARSE_COVERAGE"
    NO_COVERAGE = "NO_COVERAGE"


class DecisionConflictStatus(str, Enum):
    NO_CONFLICT = "NO_CONFLICT"
    REQUIREMENT_CONFLICT = "REQUIREMENT_CONFLICT"
    HARD_VS_SOFT_CONFLICT = "HARD_VS_SOFT_CONFLICT"
    CANDIDATE_DATA_CONFLICT = "CANDIDATE_DATA_CONFLICT"
    TEMPORAL_CONFLICT = "TEMPORAL_CONFLICT"
    EVIDENCE_CONFLICT = "EVIDENCE_CONFLICT"


@dataclass
class DecisionEvidence:
    evidence_id: str
    source_id: str
    canonical_url: Optional[str] = None
    source_path: Optional[str] = None
    provenance_status: str = "VERIFIED"
    text: str = ""
    temporal_metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source_id": self.source_id,
            "canonical_url": self.canonical_url,
            "source_path": self.source_path,
            "provenance_status": self.provenance_status,
            "text": self.text,
            "temporal_metadata": self.temporal_metadata,
        }


@dataclass
class DecisionRequirement:
    requirement_id: str
    text: str
    requirement_type: RequirementType
    constraint_type: ConstraintType
    target_value: Optional[Any] = None
    unit: Optional[str] = None
    original_wording: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "text": self.text,
            "requirement_type": self.requirement_type.value,
            "constraint_type": self.constraint_type.value,
            "target_value": self.target_value,
            "unit": self.unit,
            "original_wording": self.original_wording,
        }


@dataclass
class DecisionCriterion:
    criterion_id: str
    name: str
    category: str = "general"
    weight: str = "NORMAL"  # HARD, HIGH, NORMAL, LOW

    def to_dict(self) -> Dict[str, Any]:
        return {
            "criterion_id": self.criterion_id,
            "name": self.name,
            "category": self.category,
            "weight": self.weight,
        }


@dataclass
class CandidateEntity:
    candidate_id: str
    name: str
    canonical_name: str
    category: str = "product"
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "name": self.name,
            "canonical_name": self.canonical_name,
            "category": self.category,
            "attributes": self.attributes,
        }


@dataclass
class CriterionEvaluation:
    criterion_id: str
    candidate_id: str
    status: CriterionStatus
    raw_value: Optional[Any] = None
    normalized_value: Optional[Any] = None
    unit: Optional[str] = None
    evidence_ids: List[str] = field(default_factory=list)
    source_ids: List[str] = field(default_factory=list)
    canonical_urls: List[str] = field(default_factory=list)
    source_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "criterion_id": self.criterion_id,
            "candidate_id": self.candidate_id,
            "status": self.status.value,
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "unit": self.unit,
            "evidence_ids": self.evidence_ids,
            "source_ids": self.source_ids,
            "canonical_urls": self.canonical_urls,
            "source_path": self.source_path,
        }


@dataclass
class CandidateEvaluation:
    candidate: CandidateEntity
    status: CandidateStatus
    constraint_evaluations: Dict[str, ConstraintStatus] = field(default_factory=dict)
    criterion_evaluations: List[CriterionEvaluation] = field(default_factory=list)
    satisfied_hard_constraints: List[str] = field(default_factory=list)
    violated_hard_constraints: List[str] = field(default_factory=list)
    unverified_hard_constraints: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate": self.candidate.to_dict(),
            "status": self.status.value,
            "constraint_evaluations": {k: v.value for k, v in self.constraint_evaluations.items()},
            "criterion_evaluations": [c.to_dict() for c in self.criterion_evaluations],
            "satisfied_hard_constraints": self.satisfied_hard_constraints,
            "violated_hard_constraints": self.violated_hard_constraints,
            "unverified_hard_constraints": self.unverified_hard_constraints,
        }


@dataclass
class Tradeoff:
    tradeoff_id: str
    tradeoff_type: TradeoffType
    description: str
    candidate_a_id: str
    candidate_b_id: str
    advantage_a: str
    advantage_b: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tradeoff_id": self.tradeoff_id,
            "tradeoff_type": self.tradeoff_type.value,
            "description": self.description,
            "candidate_a_id": self.candidate_a_id,
            "candidate_b_id": self.candidate_b_id,
            "advantage_a": self.advantage_a,
            "advantage_b": self.advantage_b,
        }


@dataclass
class DecisionConflict:
    conflict_id: str
    conflict_type: DecisionConflictStatus
    description: str
    conflicting_requirements: List[str] = field(default_factory=list)
    suggested_resolution: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "conflict_type": self.conflict_type.value,
            "description": self.description,
            "conflicting_requirements": self.conflicting_requirements,
            "suggested_resolution": self.suggested_resolution,
        }


@dataclass
class RecommendationExplanation:
    hard_constraints_satisfied: List[str] = field(default_factory=list)
    preferences_satisfied: List[str] = field(default_factory=list)
    key_evidence: List[Dict[str, Any]] = field(default_factory=list)
    main_tradeoffs: List[str] = field(default_factory=list)
    why_alternatives_not_selected: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hard_constraints_satisfied": self.hard_constraints_satisfied,
            "preferences_satisfied": self.preferences_satisfied,
            "key_evidence": self.key_evidence,
            "main_tradeoffs": self.main_tradeoffs,
            "why_alternatives_not_selected": self.why_alternatives_not_selected,
        }


@dataclass
class Recommendation:
    recommendation_id: str
    status: RecommendationStatus
    stability: RecommendationStability
    candidate: Optional[CandidateEntity] = None
    tied_candidates: List[CandidateEntity] = field(default_factory=list)
    explanation: Optional[RecommendationExplanation] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "status": self.status.value,
            "stability": self.stability.value,
            "candidate": self.candidate.to_dict() if self.candidate else None,
            "tied_candidates": [c.to_dict() for c in self.tied_candidates],
            "explanation": self.explanation.to_dict() if self.explanation else None,
        }


@dataclass
class DecisionWebRequest:
    query: str
    evidence_context: List[Dict[str, Any]] = field(default_factory=list)
    verified_evidence_registry: Optional[List[Dict[str, Any]]] = None
    conversation_id: Optional[str] = None
    owner_scope_id: Optional[str] = None
    decision_session_id: Optional[str] = None
    user_timezone: Optional[str] = None


@dataclass
class DecisionWebResponse:
    decision_status: DecisionStatus
    intent: DecisionIntent
    requirements: List[DecisionRequirement] = field(default_factory=list)
    candidates: List[CandidateEvaluation] = field(default_factory=list)
    recommendations: List[Recommendation] = field(default_factory=list)
    tradeoffs: List[Tradeoff] = field(default_factory=list)
    conflicts: List[DecisionConflict] = field(default_factory=list)
    provenance_status: str = "VERIFIED"
    v10_verification_status: str = "PASSED"
    summary_text: str = ""
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_status": self.decision_status.value,
            "intent": self.intent.value,
            "requirements": [r.to_dict() for r in self.requirements],
            "candidates": [c.to_dict() for c in self.candidates],
            "recommendations": [r.to_dict() for r in self.recommendations],
            "tradeoffs": [t.to_dict() for t in self.tradeoffs],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "provenance_status": self.provenance_status,
            "v10_verification_status": self.v10_verification_status,
            "summary_text": self.summary_text,
            "warnings": self.warnings,
        }


@dataclass
class DecisionConfig:
    max_candidates: int = 20
    max_criteria: int = 20
    max_requirements: int = 30
    max_evidence_per_criterion: int = 6
    max_recommendations: int = 5
    max_decision_context_chars: int = 15000
    max_wall_clock_seconds: float = 12.0
