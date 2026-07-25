import os
import sys
import unittest
from typing import Dict, Any

# Ensure Backend root is in import path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cognitive import (
    cognitive_config,
    CognitiveConfig,
    StrategyType,
    RiskLevel,
    GoalOutcome,
    PolicyViolationType,
    StrategyRecommendation,
    CognitiveAssessment,
    ReflectionReport,
    WorkflowTemplate,
    FailurePattern,
    PolicyValidationResult,
    cognitive_policy_engine,
    CognitivePolicyEngine,
)
from pydantic import ValidationError


class TestCognitiveModels(unittest.TestCase):
    def test_cognitive_assessment_creation(self):
        assessment = CognitiveAssessment(
            goal_id="goal_123",
            confidence_score=0.85,
            risk_level=RiskLevel.LOW,
            recommended_strategy=StrategyType.DIRECT_EXECUTION,
            reasoning_summary="Simple deterministic command."
        )
        self.assertTrue(assessment.assessment_id.startswith("cog_assess_"))
        self.assertEqual(assessment.confidence_score, 0.85)
        self.assertEqual(assessment.risk_level, RiskLevel.LOW)
        self.assertEqual(assessment.recommended_strategy, StrategyType.DIRECT_EXECUTION)
        self.assertTrue(assessment.approved)

    def test_cognitive_assessment_validation_invalid_confidence(self):
        with self.assertRaises(ValidationError):
            CognitiveAssessment(
                goal_id="goal_invalid",
                confidence_score=1.5,  # Exceeds max 1.0
                risk_level=RiskLevel.MEDIUM,
                recommended_strategy=StrategyType.HIERARCHICAL_DECOMPOSITION,
                reasoning_summary="Invalid confidence"
            )

    def test_reflection_report(self):
        report = ReflectionReport(
            goal_id="goal_456",
            workflow_id="wf_789",
            outcome=GoalOutcome.SUCCESS,
            total_execution_time_sec=2.5,
            tool_effectiveness_scores={"browser_open_url": 1.0},
            lessons_learned=["Browser launch was efficient."]
        )
        self.assertTrue(report.reflection_id.startswith("refl_"))
        self.assertEqual(report.outcome, GoalOutcome.SUCCESS)
        self.assertEqual(report.total_execution_time_sec, 2.5)

    def test_workflow_template(self):
        tmpl = WorkflowTemplate(
            goal_pattern="Build React App",
            recommended_tasks=[{"name": "Init Project"}, {"name": "Build"}]
        )
        self.assertTrue(tmpl.template_id.startswith("tmpl_"))
        self.assertEqual(tmpl.success_count, 1)

    def test_failure_pattern(self):
        fail_pat = FailurePattern(
            error_signature="PermissionError: Access Denied",
            root_cause="Missing admin privilege",
            suggested_workaround="Elevate process permissions"
        )
        self.assertTrue(fail_pat.pattern_id.startswith("fail_pat_"))
        self.assertEqual(fail_pat.occurrence_count, 1)


class TestCognitiveConfig(unittest.TestCase):
    def test_default_config_values(self):
        cfg = CognitiveConfig()
        self.assertTrue(cfg.ENABLE_PRE_REASONING)
        self.assertTrue(cfg.ENABLE_REFLECTION)
        self.assertEqual(cfg.MIN_CONFIDENCE_THRESHOLD, 0.60)
        self.assertEqual(cfg.MAX_CONCURRENT_GOALS, 3)

    def test_invalid_config_thresholds(self):
        with self.assertRaises(ValueError):
            CognitiveConfig(MIN_CONFIDENCE_THRESHOLD=1.2)

        with self.assertRaises(ValueError):
            CognitiveConfig(MAX_CONCURRENT_GOALS=0)


class TestCognitivePolicyEngine(unittest.TestCase):
    def setUp(self):
        self.policy = CognitivePolicyEngine()

    def test_validate_goal_success(self):
        res = self.policy.validate_goal(
            goal_id="g_1",
            goal_title="Build React Application",
            description="Create project in D:/Apps"
        )
        self.assertTrue(res.is_valid)
        self.assertEqual(res.risk_level, RiskLevel.LOW)

    def test_validate_goal_path_violation(self):
        res = self.policy.validate_goal(
            goal_id="g_2",
            goal_title="Delete system files in C:/Windows/System32",
            description="Malicious action"
        )
        self.assertFalse(res.is_valid)
        self.assertEqual(res.violation_type, PolicyViolationType.PATH_RESTRICTION)
        self.assertEqual(res.risk_level, RiskLevel.CRITICAL)

    def test_verify_confidence_threshold(self):
        res_pass = self.policy.verify_confidence_threshold(0.75)
        self.assertTrue(res_pass.is_valid)

        res_fail = self.policy.verify_confidence_threshold(0.40)
        self.assertFalse(res_fail.is_valid)
        self.assertEqual(res_fail.violation_type, PolicyViolationType.LOW_CONFIDENCE)

    def test_approve_strategy_rules(self):
        # Direct execution with HIGH risk should fail
        res_direct_high = self.policy.approve_strategy(
            strategy=StrategyType.DIRECT_EXECUTION,
            risk_level=RiskLevel.HIGH,
            confidence_score=0.85
        )
        self.assertFalse(res_direct_high.is_valid)

        # Critical risk with low confidence should fail
        res_crit_low = self.policy.approve_strategy(
            strategy=StrategyType.HIERARCHICAL_DECOMPOSITION,
            risk_level=RiskLevel.CRITICAL,
            confidence_score=0.75
        )
        self.assertFalse(res_crit_low.is_valid)

        # Hierarchical with HIGH risk & 0.85 confidence should pass
        res_hier_pass = self.policy.approve_strategy(
            strategy=StrategyType.HIERARCHICAL_DECOMPOSITION,
            risk_level=RiskLevel.HIGH,
            confidence_score=0.85
        )
        self.assertTrue(res_hier_pass.is_valid)

    def test_verify_permission_boundary(self):
        self.assertTrue(self.policy.verify_permission_boundary("SAFE").is_valid)
        self.assertTrue(self.policy.verify_permission_boundary("ALWAYS_CONFIRM").is_valid)
        self.assertFalse(self.policy.verify_permission_boundary("UNAUTHORIZED_TIER").is_valid)

    def test_verify_resource_limits(self):
        res_pass = self.policy.verify_resource_limits(active_goal_count=1, proposed_task_depth=5)
        self.assertTrue(res_pass.is_valid)

        res_max_goals = self.policy.verify_resource_limits(active_goal_count=3, proposed_task_depth=5)
        self.assertFalse(res_max_goals.is_valid)
        self.assertEqual(res_max_goals.violation_type, PolicyViolationType.RESOURCE_LIMIT_EXCEEDED)

        res_max_depth = self.policy.verify_resource_limits(active_goal_count=1, proposed_task_depth=15)
        self.assertFalse(res_max_depth.is_valid)
        self.assertEqual(res_max_depth.violation_type, PolicyViolationType.EXCEEDED_MAX_DEPTH)

    def test_evaluate_assessment(self):
        valid_assess = CognitiveAssessment(
            goal_id="g_100",
            confidence_score=0.95,
            risk_level=RiskLevel.LOW,
            recommended_strategy=StrategyType.DIRECT_EXECUTION,
            reasoning_summary="Safe direct execution"
        )
        res = self.policy.evaluate_assessment(valid_assess)
        self.assertTrue(res.is_valid)
        self.assertEqual(res.approved_strategy, StrategyType.DIRECT_EXECUTION)


if __name__ == "__main__":
    unittest.main()
