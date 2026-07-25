import re
from typing import Dict, List, Optional, Any
from cognitive.config import cognitive_config, CognitiveConfig
from cognitive.models import (
    StrategyType,
    RiskLevel,
    PolicyViolationType,
    CognitiveAssessment,
    PolicyValidationResult,
)
from tools.telemetry import log_structured, backend_log


class CognitivePolicyEngine:
    """
    Evaluates goals, assessments, resource bounds, risk levels, and safety boundaries.
    Independent of Reasoning Engine, Reflection Engine, Experience Repo, and Adaptive Bridge.
    """

    def __init__(self, config: Optional[CognitiveConfig] = None):
        self.config = config or cognitive_config

    def validate_goal(
        self,
        goal_id: str,
        goal_title: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PolicyValidationResult:
        """Validates incoming goal metadata, title schema, and path safety boundaries."""
        violations: List[str] = []

        if not goal_id or not goal_id.strip():
            violations.append("Goal ID cannot be empty.")
        if not goal_title or not goal_title.strip():
            violations.append("Goal title cannot be empty.")

        # Check restricted path patterns in title or description
        full_text = f"{goal_title} {description or ''}"
        for restricted_path in self.config.RESTRICTED_PATH_PATTERNS:
            if re.search(re.escape(restricted_path), full_text, re.IGNORECASE):
                violations.append(f"Goal text references restricted path pattern: '{restricted_path}'")
                log_structured(backend_log, "WARNING", f"[PolicyEngine] Path violation for goal '{goal_id}': {restricted_path}")
                return PolicyValidationResult(
                    is_valid=False,
                    risk_level=RiskLevel.CRITICAL,
                    confidence_score=0.0,
                    violations=violations,
                    violation_type=PolicyViolationType.PATH_RESTRICTION,
                    details={"restricted_pattern": restricted_path}
                )

        if violations:
            return PolicyValidationResult(
                is_valid=False,
                risk_level=RiskLevel.HIGH,
                confidence_score=0.0,
                violations=violations,
                violation_type=PolicyViolationType.INVALID_GOAL_SCHEMA
            )

        return PolicyValidationResult(
            is_valid=True,
            risk_level=RiskLevel.LOW,
            confidence_score=1.0
        )

    def verify_confidence_threshold(self, confidence_score: float) -> PolicyValidationResult:
        """Verifies if a confidence score satisfies the configured minimum threshold."""
        if confidence_score < self.config.MIN_CONFIDENCE_THRESHOLD:
            violation_msg = (
                f"Confidence score {confidence_score:.2f} is below minimum threshold "
                f"{self.config.MIN_CONFIDENCE_THRESHOLD:.2f}"
            )
            log_structured(backend_log, "WARNING", f"[PolicyEngine] {violation_msg}")
            return PolicyValidationResult(
                is_valid=False,
                risk_level=RiskLevel.HIGH,
                confidence_score=confidence_score,
                violations=[violation_msg],
                violation_type=PolicyViolationType.LOW_CONFIDENCE
            )

        return PolicyValidationResult(
            is_valid=True,
            risk_level=RiskLevel.LOW,
            confidence_score=confidence_score
        )

    def approve_strategy(
        self,
        strategy: StrategyType,
        risk_level: RiskLevel,
        confidence_score: float
    ) -> PolicyValidationResult:
        """Evaluates and approves/rejects proposed execution strategy based on risk and confidence."""
        violations: List[str] = []

        # Rule 1: CRITICAL risk requires >= 0.90 confidence
        if risk_level == RiskLevel.CRITICAL and confidence_score < 0.90:
            violations.append("CRITICAL risk level requires at least 0.90 confidence score for strategy approval.")

        # Rule 2: HIGH risk requires >= MIN_CONFIDENCE_THRESHOLD
        elif risk_level == RiskLevel.HIGH and confidence_score < self.config.MIN_CONFIDENCE_THRESHOLD:
            violations.append(f"HIGH risk level requires at least {self.config.MIN_CONFIDENCE_THRESHOLD:.2f} confidence score.")

        # Rule 3: DIRECT_EXECUTION with HIGH/CRITICAL risk requires exploratory probing first
        if strategy == StrategyType.DIRECT_EXECUTION and risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            violations.append(f"Direct execution strategy is forbidden for {risk_level.value.upper()} risk levels.")

        if violations:
            log_structured(backend_log, "WARNING", f"[PolicyEngine] Strategy {strategy.value} rejected: {violations}")
            return PolicyValidationResult(
                is_valid=False,
                risk_level=risk_level,
                confidence_score=confidence_score,
                approved_strategy=None,
                violations=violations,
                violation_type=PolicyViolationType.LOW_CONFIDENCE if confidence_score < self.config.MIN_CONFIDENCE_THRESHOLD else PolicyViolationType.UNSAFE_TIER
            )

        return PolicyValidationResult(
            is_valid=True,
            risk_level=risk_level,
            confidence_score=confidence_score,
            approved_strategy=strategy
        )

    def verify_permission_boundary(self, action_tier: str) -> PolicyValidationResult:
        """Verifies if an action's safety tier is allowed by policy settings."""
        tier_upper = action_tier.strip().upper()
        if tier_upper not in self.config.ALLOWED_SAFETY_TIERS:
            violation_msg = f"Safety tier '{action_tier}' is not in allowed safety tiers: {self.config.ALLOWED_SAFETY_TIERS}"
            log_structured(backend_log, "WARNING", f"[PolicyEngine] {violation_msg}")
            return PolicyValidationResult(
                is_valid=False,
                risk_level=RiskLevel.CRITICAL,
                confidence_score=0.0,
                violations=[violation_msg],
                violation_type=PolicyViolationType.UNSAFE_TIER
            )

        return PolicyValidationResult(
            is_valid=True,
            risk_level=RiskLevel.LOW,
            confidence_score=1.0
        )

    def verify_resource_limits(self, active_goal_count: int, proposed_task_depth: int) -> PolicyValidationResult:
        """Validates current active goals and task graph depth against resource constraints."""
        violations: List[str] = []

        if active_goal_count >= self.config.MAX_CONCURRENT_GOALS:
            violations.append(
                f"Active goal count ({active_goal_count}) has reached or exceeded max limit ({self.config.MAX_CONCURRENT_GOALS})."
            )
        if proposed_task_depth > self.config.MAX_TASK_GRAPH_DEPTH:
            violations.append(
                f"Proposed task graph depth ({proposed_task_depth}) exceeds max allowed depth ({self.config.MAX_TASK_GRAPH_DEPTH})."
            )

        if violations:
            log_structured(backend_log, "WARNING", f"[PolicyEngine] Resource limit violation: {violations}")
            v_type = PolicyViolationType.EXCEEDED_MAX_DEPTH if proposed_task_depth > self.config.MAX_TASK_GRAPH_DEPTH else PolicyViolationType.RESOURCE_LIMIT_EXCEEDED
            return PolicyValidationResult(
                is_valid=False,
                risk_level=RiskLevel.HIGH,
                confidence_score=0.0,
                violations=violations,
                violation_type=v_type
            )

        return PolicyValidationResult(
            is_valid=True,
            risk_level=RiskLevel.LOW,
            confidence_score=1.0
        )

    def verify_retry_policy(self, retry_count: int) -> PolicyValidationResult:
        """Validates if current retry count exceeds maximum allowed cognitive replan attempts."""
        if retry_count > self.config.MAX_COGNITIVE_REPLANS:
            violation_msg = f"Retry count ({retry_count}) exceeds max cognitive replans ({self.config.MAX_COGNITIVE_REPLANS})."
            log_structured(backend_log, "WARNING", f"[PolicyEngine] {violation_msg}")
            return PolicyValidationResult(
                is_valid=False,
                risk_level=RiskLevel.HIGH,
                confidence_score=0.0,
                violations=[violation_msg],
                violation_type=PolicyViolationType.RESOURCE_LIMIT_EXCEEDED
            )

        return PolicyValidationResult(
            is_valid=True,
            risk_level=RiskLevel.LOW,
            confidence_score=1.0
        )

    def evaluate_assessment(self, assessment: CognitiveAssessment) -> PolicyValidationResult:
        """Performs a comprehensive evaluation of a CognitiveAssessment object."""
        # 1. Check confidence
        conf_res = self.verify_confidence_threshold(assessment.confidence_score)
        if not conf_res.is_valid:
            effective_risk = assessment.risk_level if assessment.risk_level == RiskLevel.CRITICAL else conf_res.risk_level
            return PolicyValidationResult(
                is_valid=False,
                risk_level=effective_risk,
                confidence_score=conf_res.confidence_score,
                violations=conf_res.violations,
                violation_type=conf_res.violation_type,
                details=conf_res.details
            )

        # 2. Check strategy approval
        strat_res = self.approve_strategy(
            strategy=assessment.recommended_strategy,
            risk_level=assessment.risk_level,
            confidence_score=assessment.confidence_score
        )
        if not strat_res.is_valid:
            effective_risk = assessment.risk_level if assessment.risk_level == RiskLevel.CRITICAL else strat_res.risk_level
            return PolicyValidationResult(
                is_valid=False,
                risk_level=effective_risk,
                confidence_score=strat_res.confidence_score,
                violations=strat_res.violations,
                violation_type=strat_res.violation_type,
                details=strat_res.details
            )

        return PolicyValidationResult(
            is_valid=True,
            risk_level=assessment.risk_level,
            confidence_score=assessment.confidence_score,
            approved_strategy=assessment.recommended_strategy,
            details={"assessment_id": assessment.assessment_id, "goal_id": assessment.goal_id}
        )


cognitive_policy_engine = CognitivePolicyEngine()
