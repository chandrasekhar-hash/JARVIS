import os
import sys
import time
import asyncio
import unittest

# Ensure Backend root is in import path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cognitive import (
    CognitiveReasoningEngine,
    CognitiveAssessment,
    StrategyType,
    RiskLevel,
    WorkflowTemplate,
    FailurePattern,
    ExperienceRepository,
    CognitivePolicyEngine,
)
from memory.storage.sqlite_provider import SQLiteMemoryStorageProvider

TEST_DB_PATH = "logs/test_cognitive_m63.db"


def cleanup_test_db():
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass


class TestCognitiveReasoningEngine(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        cleanup_test_db()
        self.storage = SQLiteMemoryStorageProvider(db_path=TEST_DB_PATH)
        self.exp_repo = ExperienceRepository(memory_storage=self.storage)
        self.policy_engine = CognitivePolicyEngine()
        self.reasoning_engine = CognitiveReasoningEngine(
            policy_engine=self.policy_engine,
            exp_repo=self.exp_repo
        )

    async def asyncTearDown(self):
        cleanup_test_db()

    async def test_low_risk_direct_execution_goal(self):
        start = time.time()
        assessment = await self.reasoning_engine.analyze_and_assess_goal(
            goal_id="g_simple",
            goal_title="Open Google Chrome"
        )
        elapsed_ms = (time.time() - start) * 1000.0

        self.assertIsInstance(assessment, CognitiveAssessment)
        self.assertEqual(assessment.goal_id, "g_simple")
        self.assertEqual(assessment.recommended_strategy, StrategyType.DIRECT_EXECUTION)
        self.assertEqual(assessment.risk_level, RiskLevel.LOW)
        self.assertGreaterEqual(assessment.confidence_score, 0.70)
        self.assertTrue(assessment.approved)
        self.assertLess(elapsed_ms, 150.0, "Simple reasoning should run in <150ms")

    async def test_complex_automation_goal(self):
        start = time.time()
        assessment = await self.reasoning_engine.analyze_and_assess_goal(
            goal_id="g_complex",
            goal_title="Build React application in D:/Apps and deploy build pipeline",
            description="Initialize Vite React project, install npm dependencies, compile production assets."
        )
        elapsed_ms = (time.time() - start) * 1000.0

        self.assertEqual(assessment.recommended_strategy, StrategyType.HIERARCHICAL_DECOMPOSITION)
        self.assertIn(assessment.risk_level, (RiskLevel.LOW, RiskLevel.MEDIUM))
        self.assertTrue(assessment.approved)
        self.assertLess(elapsed_ms, 800.0, "Complex reasoning should run in <800ms")

    async def test_ambiguous_goal_strategy(self):
        assessment = await self.reasoning_engine.analyze_and_assess_goal(
            goal_id="g_ambiguous",
            goal_title="Do stuff with files or something maybe"
        )
        self.assertIn(StrategyType.EXPLORATORY_SEARCH, [assessment.recommended_strategy] + assessment.alternative_strategies)
        self.assertTrue("ambiguous" in assessment.reasoning_summary.lower())

    async def test_critical_risk_path_violation_policy_rejection(self):
        assessment = await self.reasoning_engine.analyze_and_assess_goal(
            goal_id="g_dangerous",
            goal_title="Delete system files in C:/Windows/System32"
        )
        self.assertEqual(assessment.risk_level, RiskLevel.CRITICAL)
        self.assertFalse(assessment.approved, "Goal referencing System32 must be rejected by policy engine")
        self.assertIn("policy", assessment.reasoning_summary.lower())

    async def test_experience_boost_and_failure_pattern_penalty(self):
        # 1. Seed past experience
        tmpl = WorkflowTemplate(goal_pattern="Organize Downloads folder", success_count=10)
        await self.exp_repo.store_workflow_template(tmpl)

        assessment_exp = await self.reasoning_engine.analyze_and_assess_goal(
            goal_id="g_exp",
            goal_title="Organize Downloads folder"
        )
        self.assertIn(tmpl.template_id, assessment_exp.matched_experience_ids)
        self.assertIn("matched past experience", assessment_exp.reasoning_summary.lower())

        # 2. Seed failure pattern
        fail_pat = FailurePattern(
            error_signature="Organize Downloads permission failure",
            root_cause="Folder locked by Explorer",
            suggested_workaround="Unlock folder"
        )
        await self.exp_repo.store_failure_pattern(fail_pat)

        assessment_fail = await self.reasoning_engine.analyze_and_assess_goal(
            goal_id="g_fail",
            goal_title="Organize Downloads permission failure"
        )
        self.assertIn("failure patterns detected", assessment_fail.reasoning_summary.lower())

    async def test_missing_experience_fallback(self):
        # Reasoning should gracefully succeed even if no experiences exist
        assessment = await self.reasoning_engine.analyze_and_assess_goal(
            goal_id="g_unique",
            goal_title="Perform unique unprecedented task"
        )
        self.assertIsInstance(assessment, CognitiveAssessment)
        self.assertTrue(assessment.approved)
        self.assertEqual(len(assessment.matched_experience_ids), 0)


if __name__ == "__main__":
    unittest.main()
